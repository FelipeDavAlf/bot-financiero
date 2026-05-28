import os
from dotenv import load_dotenv

# Carga las variables del archivo .env al entorno
load_dotenv()

class Settings:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "credentials.json")

# Instanciamos la configuración para usarla en otros archivos
settings = Settings()