from google import genai
from google.genai import types
import json
from datetime import date
from core.models import Transaccion
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

    def message_processor(self, user_message: str) -> Transaccion:
        """
        Analyzes a natural language message and extracts transaction details.

        This method sends a strictly formatted prompt to the Gemini 2.5 Flash model,
        forcing a JSON response. It then parses the JSON and validates it against 
        the Transaccion Pydantic model.

        Args:
            user_message (str): The raw text message provided by the user 
                (e.g., "I spent 120 on chilaquiles with my debit card").

        Returns:
            Transaccion: A validated Pydantic model containing the structured 
                transaction data (date, type, amount, categories, etc.).

        Raises:
            json.JSONDecodeError: If the model fails to return a valid JSON string.
            pydantic.ValidationError: If the extracted data does not match the 
                expected Transaccion schema.
            Exception: For any API or connection errors with Google GenAI.
        """
        today = date.today().isoformat()
        
        prompt = f"""
        Hoy es {today}. Eres un asistente financiero muy preciso.
        Analiza el siguiente mensaje y extrae los datos de la transacción.
        Devuelve ÚNICAMENTE un JSON válido que cumpla con esta estructura:
        - fecha (YYYY-MM-DD, usa la fecha de hoy si no se especifica)
        - tipo_movimiento ("Ingreso", "Gasto" o "Traspaso")
        - monto (número positivo)
        - cuenta_origen (string o null, ej. "Tarjeta Débito", "Efectivo")
        - cuenta_destino (string o null, ej. "Cetes", "Ahorro Carro")
        - categoria (string)
        - descripcion (string)

        Mensaje del usuario: "{user_message}"
        """
        
        response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0 
            )
        )
        
        data = json.loads(response.text)
        return Transaccion(**data)