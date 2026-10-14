from typing import Optional
from google import genai
from google.genai import types
import json
import logging
from datetime import date, timedelta
from core.models import Transaction
from core.validators.duplicate_validator import normalize_amount, normalize_date
from core.config import settings

DEFAULT_SUPPORTED_ACCOUNTS = [
    "Efectivo",
    "Tarjeta Débito BBVA",
    "Tarjeta Débito Stori",
    "Tarjeta Crédito BBVA",
    "Tarjeta Crédito Stori",
    "Tarjeta Crédito Rappi",
    "Tarjeta Crédito Nu",
    "Tarjeta Débito Nu",
    "Cuenta Mercado Pago",
]


class NLPService:
    """
    Service responsible for Natural Language Processing using Google's Gemini API.
    
    This class handles the connection to the Gemini model and processes raw 
    natural language inputs from the user, extracting financial transaction 
    data into structured Pydantic models.
    """

    def __init__(self):
        """
        Initializes the NLPService with the Gemini API client.
        
        The API key is retrieved automatically from the global settings configuration.
        """
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def _extract_json(self, text: str) -> dict:
        """Limpia la respuesta de Gemini para extraer el JSON válido (por si incluye bloques de markdown o texto extra)"""
        import re
        match = re.search(r'```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```', text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            # Si no hay bloque markdown, intentamos buscar el primer { o [
            start_idx = text.find('{')
            if start_idx == -1:
                start_idx = text.find('[')
            end_idx = text.rfind('}')
            if end_idx == -1 or text.rfind(']') > end_idx:
                end_idx = text.rfind(']')
                
            if start_idx != -1 and end_idx != -1:
                json_str = text[start_idx:end_idx+1]
            else:
                json_str = text.strip()
                
        return json.loads(json_str)

    @staticmethod
    def _sanitize_transaction_data(data: dict, allowed_accounts: Optional[list] = None) -> dict:
        """
        Sanitizes and normalizes raw dictionary data returned by LLM
        prior to instantiating the Pydantic Transaction model.
        Resolves relative dates (ayer, antier, hoy), normalizes transaction types,
        cleans numeric amounts, and handles account and category mapping.
        """
        clean = dict(data)
        clean.pop("is_transaction", None)

        # 1. Normalize amount
        clean["amount"] = normalize_amount(clean.get("amount"))

        # 2. Normalize date (handling relative expressions like ayer, antier, hoy)
        today = date.today()
        raw_date = str(clean.get("date", "")).strip().lower()
        if not raw_date or raw_date in ("none", "null"):
            clean["date"] = today.isoformat()
        elif "ayer" in raw_date and "ante" not in raw_date and "antier" not in raw_date:
            clean["date"] = (today - timedelta(days=1)).isoformat()
        elif "antier" in raw_date or "anteayer" in raw_date:
            clean["date"] = (today - timedelta(days=2)).isoformat()
        elif "hoy" in raw_date:
            clean["date"] = today.isoformat()
        else:
            clean["date"] = normalize_date(raw_date)

        # 3. Normalize transaction type (strict Literal matching)
        raw_type = str(clean.get("transaction_type", "")).strip().lower()
        if any(w in raw_type for w in ["ingreso", "deposito", "abono", "sueldo", "nomina"]):
            clean["transaction_type"] = "Ingreso"
        elif any(w in raw_type for w in ["traspaso", "transferencia", "apartado"]):
            clean["transaction_type"] = "Traspaso"
        else:
            clean["transaction_type"] = "Gasto"

        # 4. Normalize account names
        accounts_pool = allowed_accounts or DEFAULT_SUPPORTED_ACCOUNTS
        for acct_field in ["source_account", "destination_account"]:
            raw_acct = clean.get(acct_field)
            if not raw_acct or str(raw_acct).strip().lower() in ("null", "none", ""):
                clean[acct_field] = None
            else:
                acct_str = str(raw_acct).strip()
                acct_lower = acct_str.lower()
                matched = None

                # 1. Exact match in accounts pool
                for candidate in accounts_pool:
                    if candidate.lower() == acct_lower:
                        matched = candidate
                        break

                # 1b. Distinct keyword match in accounts pool (e.g. "santander" in "Tarjeta Débito Santander")
                if not matched:
                    import re
                    ignored_tokens = {"tarjeta", "cuenta", "debito", "débito", "credito", "crédito", "de", "el", "la", "mi"}
                    query_tokens = [w for w in re.findall(r"\w+", acct_lower) if w not in ignored_tokens and len(w) > 2]
                    if query_tokens:
                        for candidate in accounts_pool:
                            c_lower = candidate.lower()
                            if all(t in c_lower for t in query_tokens):
                                matched = candidate
                                break

                # 2. Match based on bank/brand keywords if present in accounts pool
                if not matched:
                    if "rappi" in acct_lower:
                        matched = next((c for c in accounts_pool if "rappi" in c.lower()), "Tarjeta Crédito Rappi")
                    elif "mercado pago" in acct_lower or "mercadopago" in acct_lower:
                        matched = next((c for c in accounts_pool if "mercado pago" in c.lower()), "Cuenta Mercado Pago")
                    elif "stori" in acct_lower:
                        is_cred = "crédito" in acct_lower or "credito" in acct_lower
                        matched = next((c for c in accounts_pool if "stori" in c.lower() and ("crédito" in c.lower() or "credito" in c.lower()) == is_cred), None)
                    elif "nu" in acct_lower:
                        is_deb = "débito" in acct_lower or "debito" in acct_lower
                        matched = next((c for c in accounts_pool if "nu" in c.lower() and ("débito" in c.lower() or "debito" in c.lower()) == is_deb), None)
                    elif "bbva" in acct_lower:
                        is_cred = "crédito" in acct_lower or "credito" in acct_lower
                        matched = next((c for c in accounts_pool if "bbva" in c.lower() and ("crédito" in c.lower() or "credito" in c.lower()) == is_cred), None)
                    elif "efectivo" in acct_lower:
                        matched = next((c for c in accounts_pool if "efectivo" in c.lower()), "Efectivo")

                clean[acct_field] = matched or acct_str

        # 5. Normalize category, subcategory and description
        raw_cat = clean.get("category")
        if not raw_cat or str(raw_cat).strip().lower() in ("null", "none", ""):
            clean["category"] = "Otros"
        else:
            clean["category"] = str(raw_cat).strip()

        raw_subcat = clean.get("subcategory")
        if not raw_subcat or str(raw_subcat).strip().lower() in ("null", "none", ""):
            clean["subcategory"] = clean.get("category", "General")
        else:
            clean["subcategory"] = str(raw_subcat).strip()

        raw_desc = clean.get("description")
        if not raw_desc or str(raw_desc).strip().lower() in ("null", "none", ""):
            clean["description"] = clean.get("subcategory", "Movimiento")
        else:
            clean["description"] = str(raw_desc).strip()

        return clean

    def message_processor(
        self,
        user_message: str,
        user_accounts: Optional[list] = None,
    ) -> Optional[Transaction]:
        """
        Analyzes a natural language message and extracts transaction details.

        This method sends a strictly formatted prompt to the Gemini 2.5 Flash model,
        forcing a JSON response. It then parses the JSON, sanitizes the fields,
        and validates it against the Transaction Pydantic model.
        """
        today = date.today().isoformat()
        accounts_to_use = user_accounts if user_accounts else DEFAULT_SUPPORTED_ACCOUNTS
        accounts_json = json.dumps(accounts_to_use, ensure_ascii=False)
        
        prompt = f"""
        Hoy es {today}. Eres un asistente financiero muy preciso.
        Determina si el siguiente mensaje describe una transacción financiera real (ingreso, gasto o traspaso de dinero).
        
        Si el mensaje NO describe un movimiento financiero (por ejemplo: si es un saludo, una pregunta general, agradecimiento, texto casual o no menciona montos ni conceptos de dinero), devuelve ÚNICAMENTE este JSON:
        {{"is_transaction": false}}

        Si el mensaje SÍ describe un movimiento financiero, devuelve ÚNICAMENTE un JSON válido con esta estructura:
        {{
            "is_transaction": true,
            "date": "YYYY-MM-DD",
            "transaction_type": "Ingreso", "Gasto" o "Traspaso",
            "amount": número_positivo,
            "source_account": string o null,
            "destination_account": string o null,
            "category": string,
            "subcategory": string,
            "description": string
        }}

        Reglas para los campos si es una transacción:
        - date: YYYY-MM-DD (usa la fecha de hoy si no se especifica).
        - transaction_type: "Ingreso", "Gasto" o "Traspaso".
        - amount: número positivo mayor a 0.
        - source_account: string o null. DEBE ser EXACTAMENTE una de esta lista: {accounts_json}. Si no lo menciona, infiérelo lógicamente o déjalo en null.
        - destination_account: string o null. DEBE ser EXACTAMENTE una de la misma lista anterior. Usualmente aplica para "Traspaso" o "Ingreso". Si no lo menciona, infiérelo lógicamente o déjalo en null.
        - category: string. DEBE ser EXACTAMENTE una de esta lista: [Salario, Rendimientos, Alimentación, Vivienda y Servicios, Transporte, Suscripciones, Ocio y Entretenimiento, Salud y Cuidado, Mascotas, Ahorro e Inversión, Otros, Traspaso].
        - subcategory: Asigna una etiqueta corta (1 a 3 palabras) para el detalle.
        - description: Descripción clara del movimiento o nombre del comercio.

        Mensaje del usuario: "{user_message}"
        """
        
        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            temperature=0.1,
        )
        response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=config,
        )
        
        data = self._extract_json(response.text)
        if data.get("is_transaction") is False or not data.get("amount"):
            return None

        clean_data = self._sanitize_transaction_data(data, allowed_accounts=accounts_to_use)
        if clean_data.get("amount", 0) <= 0:
            return None

        return Transaction(**clean_data)

    def process_audio(
        self,
        audio_path: str,
        user_accounts: Optional[list] = None,
    ) -> Optional[Transaction]:
        """
        Processes a voice note using Gemini's native audio capabilities.
        Returns None if the voice note does not describe a financial transaction.
        """
        today = date.today().isoformat()
        accounts_to_use = user_accounts if user_accounts else DEFAULT_SUPPORTED_ACCOUNTS
        accounts_json = json.dumps(accounts_to_use, ensure_ascii=False)
        
        prompt = f"""
        Hoy es {today}. Eres un asistente financiero muy preciso.
        Escucha el siguiente audio y determina si describe una transacción financiera real.
        
        Si el audio NO describe una transacción financiera (por ejemplo: saludo, silencio, conversación casual sin montos), devuelve ÚNICAMENTE:
        {{"is_transaction": false}}

        Si SÍ describe una transacción financiera, devuelve ÚNICAMENTE un JSON válido que cumpla con esta estructura:
        {{
            "is_transaction": true,
            "date": "YYYY-MM-DD",
            "transaction_type": "Ingreso", "Gasto" o "Traspaso",
            "amount": número_positivo,
            "source_account": string o null,
            "destination_account": string o null,
            "category": string,
            "subcategory": string,
            "description": string
        }}

        Reglas para los campos si es una transacción:
        - date: YYYY-MM-DD (usa la fecha de hoy si no se especifica).
        - transaction_type: "Ingreso", "Gasto" o "Traspaso".
        - amount: número positivo mayor a 0.
        - source_account: string o null. DEBE ser EXACTAMENTE una de esta lista: {accounts_json}.
        - destination_account: string o null. DEBE ser EXACTAMENTE una de la misma lista anterior.
        - category: string. DEBE ser EXACTAMENTE una de esta lista: [Salario, Rendimientos, Alimentación, Vivienda y Servicios, Transporte, Suscripciones, Ocio y Entretenimiento, Salud y Cuidado, Mascotas, Ahorro e Inversión, Otros, Traspaso].
        - subcategory: Asigna una etiqueta corta (1 a 3 palabras) para el detalle.
        - description: Descripción clara del movimiento.
        """
        
        # Subimos el archivo a la API de Gemini
        audio_file = self.client.files.upload(file=audio_path)
        
        import time
        while audio_file.state.name == "PROCESSING":
            time.sleep(2)
            audio_file = self.client.files.get(name=audio_file.name)
            
        if audio_file.state.name == "FAILED":
            raise Exception("Google falló al procesar el audio.")
        
        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            temperature=0.1,
        )
        response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, audio_file],
            config=config,
        )
        
        # Limpieza del archivo en el servidor de Google
        audio_file.delete()
        
        data = self._extract_json(response.text)
        if data.get("is_transaction") is False or not data.get("amount"):
            return None

        clean_data = self._sanitize_transaction_data(data, allowed_accounts=accounts_to_use)
        if clean_data.get("amount", 0) <= 0:
            return None

        return Transaction(**clean_data)

    def extract_document_text(self, doc_path: str) -> str:
        """
        Extracts raw tabular text from a PDF, CSV, or Excel file locally.
        """
        import os
        ext = os.path.splitext(doc_path)[1].lower()
        extracted_text = ""

        try:
            if ext == ".pdf":
                from pypdf import PdfReader
                reader = PdfReader(doc_path)
                for page in reader.pages:
                    page_text = page.extract_text() or ""
                    if page_text:
                        extracted_text += page_text + "\n"
            elif ext in [".csv", ".xlsx", ".xls"]:
                import pandas as pd
                if ext == ".csv":
                    # Mercado Pago frequently uses semicolons, attempt both
                    try:
                        df = pd.read_csv(doc_path, sep=";")
                        if len(df.columns) < 2:
                            df = pd.read_csv(doc_path, sep=",")
                    except Exception:
                        df = pd.read_csv(doc_path)
                else:
                    df = pd.read_excel(doc_path)

                extracted_text = df.to_csv(index=False, sep=";")
            else:
                raise ValueError(f"Formato no soportado: {ext}")
        except Exception as e:
            raise Exception(f"Error extrayendo texto del documento localmente: {e}")

        if not extracted_text.strip():
            raise Exception("No se pudo extraer texto del documento. Asegúrate de que no esté vacío o sea solo imágenes.")

        logging.info(f"Extracted {len(extracted_text)} characters from {doc_path}")
        return extracted_text

    def parse_transactions_from_text(
        self,
        extracted_text: str,
        user_accounts: Optional[list] = None,
    ) -> list[Transaction]:
        """
        Sends extracted document text to Gemini and parses structured transactions.
        """
        accounts_to_use = user_accounts if user_accounts else DEFAULT_SUPPORTED_ACCOUNTS
        accounts_json = json.dumps(accounts_to_use, ensure_ascii=False)

        prompt = f"""
        Eres un asistente financiero experto. Analiza el siguiente estado de cuenta o documento financiero extraído a texto.
        Extrae TODAS las transacciones válidas que encuentres.
        Clasifica los pagos a la propia tarjeta de crédito como un "Traspaso", asignando la cuenta de origen (si se menciona) y como destino la tarjeta de crédito que se está pagando. Ignora saldo anterior o conceptos informativos que no sean gastos, ingresos o traspasos reales del periodo.
        Devuelve ÚNICAMENTE un JSON válido que contenga un objeto con la llave "transactions", el cual debe ser un arreglo de transacciones.
        Cada transacción debe cumplir esta estructura ESTRICTAMENTE:
        - date (YYYY-MM-DD). Convierte cualquier fecha (ej. DD-MM-YYYY o DD/MM/YY) obligatoriamente al formato YYYY-MM-DD.
        - transaction_type ("Ingreso", "Gasto" o "Traspaso"). Si el monto era negativo, generalmente es un "Gasto".
        - amount (número). El monto SIEMPRE debe ser un valor numérico POSITIVO (mayor a 0). Elimina el signo negativo si lo tiene.
        - source_account (string o null). DEBE ser EXACTAMENTE una de esta lista: {accounts_json}. Infiérelo del documento o déjalo en null.
        - destination_account (string o null).
        - category (string). DEBE ser EXACTAMENTE una de esta lista: [Salario, Rendimientos, Alimentación, Vivienda y Servicios, Transporte, Suscripciones, Ocio y Entretenimiento, Salud y Cuidado, Mascotas, Ahorro e Inversión, Otros, Traspaso].
        - subcategory (string). Asigna una etiqueta corta (1 a 3 palabras) para el detalle.
        - description (string). Nombre del comercio o concepto reportado.
        
        Aquí está el contenido del documento:
        {extracted_text}
        """

        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            temperature=0.1,
        )
        response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=config,
        )

        data = self._extract_json(response.text)
        raw_items = data.get("transactions", []) if isinstance(data, dict) else []
        clean_transactions = []
        for item in raw_items:
            if isinstance(item, dict):
                clean_item = self._sanitize_transaction_data(item, allowed_accounts=accounts_to_use)
                if clean_item.get("amount", 0) > 0:
                    clean_transactions.append(Transaction(**clean_item))

        logging.info(f"Parsed {len(clean_transactions)} transactions with Gemini.")
        return clean_transactions

    def process_document(
        self,
        doc_path: str,
        user_accounts: Optional[list] = None,
    ) -> list[Transaction]:
        """
        Processes a PDF, CSV, or Excel file and extracts multiple transactions.
        """
        extracted_text = self.extract_document_text(doc_path)
        return self.parse_transactions_from_text(extracted_text, user_accounts=user_accounts)