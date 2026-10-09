import os
from dotenv import load_dotenv

# Carga las variables del archivo .env al entorno
load_dotenv()

class Settings:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "credentials.json").strip()
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()  # Solo se usa en producción (Render)

# Instanciamos la configuración para usarla en otros archivos
settings = Settings()