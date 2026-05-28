from google import genai
from google.genai import types
import json
from datetime import date
from core.models import Transaccion
from core.config import settings

class NLPService:
    def __init__(self):
        # En la nueva librería, instanciamos un Cliente pasándole la llave directamente
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def procesar_mensaje(self, mensaje_usuario: str) -> Transaccion:
        hoy = date.today().isoformat()
        
        prompt = f"""
        Hoy es {hoy}. Eres un asistente financiero muy preciso.
        Analiza el siguiente mensaje y extrae los datos de la transacción.
        Devuelve ÚNICAMENTE un JSON válido que cumpla con esta estructura:
        - fecha (YYYY-MM-DD, usa la fecha de hoy si no se especifica)
        - tipo_movimiento ("Ingreso", "Gasto" o "Traspaso")
        - monto (número positivo)
        - cuenta_origen (string o null, ej. "Tarjeta Débito", "Efectivo")
        - cuenta_destino (string o null, ej. "Cetes", "Ahorro Carro")
        - categoria (string)
        - descripcion (string)

        Mensaje del usuario: "{mensaje_usuario}"
        """
        
        # Usamos el cliente para llamar al modelo y forzamos la salida JSON en la configuración
        respuesta = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0 # Temperatura cero para que sea lo más preciso y determinista posible
            )
        )
        
        # Extraemos el texto de la respuesta, lo pasamos a diccionario y lo validamos
        datos = json.loads(respuesta.text)
        return Transaccion(**datos)