from google import genai
import json
from datetime import date
from core.models import Transaction, TransactionList
from core.config import settings

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

    def message_processor(self, user_message: str) -> Transaction:
        """
        Analyzes a natural language message and extracts transaction details.

        This method sends a strictly formatted prompt to the Gemini 2.5 Flash model,
        forcing a JSON response. It then parses the JSON and validates it against 
        the Transaction Pydantic model.

        Args:
            user_message (str): The raw text message provided by the user 
                (e.g., "I spent 120 on chilaquiles with my debit card").

        Returns:
            Transaction: A validated Pydantic model containing the structured 
                transaction data (date, type, amount, categories, etc.).

        Raises:
            json.JSONDecodeError: If the model fails to return a valid JSON string.
            pydantic.ValidationError: If the extracted data does not match the 
                expected Transaction schema.
            Exception: For any API or connection errors with Google GenAI.
        """
        today = date.today().isoformat()
        
        prompt = f"""
        Hoy es {today}. Eres un asistente financiero muy preciso.
        Analiza el siguiente mensaje y extrae los datos de la transacción.
        Devuelve ÚNICAMENTE un JSON válido que cumpla con esta estructura:
        - date (YYYY-MM-DD, usa la fecha de hoy si no se especifica)
        - transaction_type ("Ingreso", "Gasto" o "Traspaso")
        - amount (número positivo)
        - source_account (string o null). DEBE ser EXACTAMENTE una de esta lista: ["Efectivo", "Tarjeta Débito BBVA", "Tarjeta Débito Stori", "Tarjeta Crédito BBVA", "Tarjeta Crédito Stori", "Tarjeta Crédito Rappi", "Tarjeta Crédito Nu", "Tarjeta Débito Nu", "Cuenta Mercado Pago"]. Si el mensaje no lo menciona, infiérelo lógicamente o déjalo en null.
        - destination_account (string o null). DEBE ser EXACTAMENTE una de la misma lista anterior. Usualmente aplica para "Traspaso" o "Ingreso". Si el mensaje no lo menciona, infiérelo lógicamente o déjalo en null.
        - category (string). DEBE ser EXACTAMENTE una de esta lista: [Salario, Rendimientos, Alimentación, Vivienda y Servicios, Transporte, Suscripciones, Ocio y Entretenimiento, Salud y Cuidado, Mascotas, Ahorro e Inversión, Otros, Traspaso].
        - subcategory (string). Asigna una etiqueta corta (1 a 3 palabras) para el detalle. Ejemplos: si category es "Transporte", subcategory puede ser "Uber" o "Gasolina". Si es "Mascotas", puede ser "Arena" o "Comida". Si es "Ocio y Entretenimiento", puede ser "Videojuegos", "Conciertos" o "Cafetería".
        - description (string)

        Mensaje del usuario: "{user_message}"
        """
        
        response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        data = self._extract_json(response.text)
        return Transaction(**data)

    def process_audio(self, audio_path: str) -> Transaction:
        """
        Processes a voice note using Gemini's native audio capabilities.
        """
        today = date.today().isoformat()
        
        prompt = f"""
        Hoy es {today}. Eres un asistente financiero muy preciso.
        Escucha el siguiente audio y extrae los datos de la transacción.
        Devuelve ÚNICAMENTE un JSON válido que cumpla con esta estructura:
        - date (YYYY-MM-DD, usa la fecha de hoy si no se especifica)
        - transaction_type ("Ingreso", "Gasto" o "Traspaso")
        - amount (número positivo)
        - source_account (string o null). DEBE ser EXACTAMENTE una de esta lista: ["Efectivo", "Tarjeta Débito BBVA", "Tarjeta Débito Stori", "Tarjeta Crédito BBVA", "Tarjeta Crédito Stori", "Tarjeta Crédito Rappi", "Tarjeta Crédito Nu", "Tarjeta Débito Nu", "Cuenta Mercado Pago"]. Si el audio no lo menciona, infiérelo lógicamente o déjalo en null.
        - destination_account (string o null). DEBE ser EXACTAMENTE una de la misma lista anterior. Usualmente aplica para "Traspaso" o "Ingreso". Si el audio no lo menciona, infiérelo lógicamente o déjalo en null.
        - category (string). DEBE ser EXACTAMENTE una de esta lista: [Salario, Rendimientos, Alimentación, Vivienda y Servicios, Transporte, Suscripciones, Ocio y Entretenimiento, Salud y Cuidado, Mascotas, Ahorro e Inversión, Otros, Traspaso].
        - subcategory (string). Asigna una etiqueta corta (1 a 3 palabras) para el detalle.
        - description (string)
        """
        
        # Subimos el archivo a la API de Gemini
        audio_file = self.client.files.upload(file=audio_path)
        
        import time
        while audio_file.state.name == "PROCESSING":
            time.sleep(2)
            audio_file = self.client.files.get(name=audio_file.name)
            
        if audio_file.state.name == "FAILED":
            raise Exception("Google falló al procesar el audio.")
        
        response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, audio_file]
        )
        
        # Limpieza del archivo en el servidor de Google
        audio_file.delete()
        
        data = self._extract_json(response.text)
        return Transaction(**data)

    def process_document(self, doc_path: str) -> list[Transaction]:
        """
        Processes a PDF, CSV, or Excel file and extracts multiple transactions.
        """
        import os
        ext = os.path.splitext(doc_path)[1].lower()
        extracted_text = ""
        
        try:
            if ext == ".pdf":
                from pypdf import PdfReader
                reader = PdfReader(doc_path)
                for page in reader.pages:
                    extracted_text += page.extract_text() + "\n"
            elif ext in [".csv", ".xlsx", ".xls"]:
                import pandas as pd
                if ext == ".csv":
                    # Mercado Pago usa punto y coma frecuentemente, probamos ambos
                    try:
                        df = pd.read_csv(doc_path, sep=";")
                        if len(df.columns) < 2:
                            df = pd.read_csv(doc_path, sep=",")
                    except:
                        df = pd.read_csv(doc_path)
                else:
                    df = pd.read_excel(doc_path)
                
                extracted_text = df.to_csv(index=False, sep=";")
            else:
                raise Exception(f"Formato no soportado: {ext}")
        except Exception as e:
            raise Exception(f"Error extrayendo texto del documento localmente: {e}")

        if not extracted_text.strip():
            raise Exception("No se pudo extraer texto del documento. Asegúrate de que no esté vacío o sea solo imágenes.")
            
        prompt = f"""
        Eres un asistente financiero experto. Analiza el siguiente estado de cuenta o documento financiero extraído a texto.
        Extrae TODAS las transacciones válidas que encuentres.
        Clasifica los pagos a la propia tarjeta de crédito como un "Traspaso", asignando la cuenta de origen (si se menciona) y como destino la tarjeta de crédito que se está pagando. Ignora saldo anterior o conceptos informativos que no sean gastos, ingresos o traspasos reales del periodo.
        Devuelve ÚNICAMENTE un JSON válido que contenga un objeto con la llave "transactions", el cual debe ser un arreglo de transacciones.
        Cada transacción debe cumplir esta estructura ESTRICTAMENTE:
        - date (YYYY-MM-DD). Convierte cualquier fecha (ej. DD-MM-YYYY o DD/MM/YY) obligatoriamente al formato YYYY-MM-DD.
        - transaction_type ("Ingreso", "Gasto" o "Traspaso"). Si el monto era negativo, generalmente es un "Gasto".
        - amount (número). El monto SIEMPRE debe ser un valor numérico POSITIVO (mayor a 0). Elimina el signo negativo si lo tiene.
        - source_account (string o null). DEBE ser EXACTAMENTE una de esta lista: ["Efectivo", "Tarjeta Débito BBVA", "Tarjeta Débito Stori", "Tarjeta Crédito BBVA", "Tarjeta Crédito Stori", "Tarjeta Crédito Rappi", "Tarjeta Crédito Nu", "Tarjeta Débito Nu", "Cuenta Mercado Pago"]. Infiérelo del documento o déjalo en null.
        - destination_account (string o null).
        - category (string). DEBE ser EXACTAMENTE una de esta lista: [Salario, Rendimientos, Alimentación, Vivienda y Servicios, Transporte, Suscripciones, Ocio y Entretenimiento, Salud y Cuidado, Mascotas, Ahorro e Inversión, Otros, Traspaso].
        - subcategory (string). Asigna una etiqueta corta (1 a 3 palabras) para el detalle.
        - description (string). Nombre del comercio o concepto reportado.
        
        Aquí está el contenido del documento:
        {extracted_text}
        """
        
        response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        data = self._extract_json(response.text)
        # Parseamos con el modelo de lista
        transaction_list = TransactionList(**data)
        return transaction_list.transactions