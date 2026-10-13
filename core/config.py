import os
from dotenv import load_dotenv

# Carga las variables del archivo .env al entorno
load_dotenv()

class Settings:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "credentials.json").strip()
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()  # Only used in production (Render)
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./finanzas.db").strip()

    @property
    def normalized_database_url(self) -> str:
        """Returns the normalized database URL, ensuring psycopg2 driver is explicitly used."""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url

# Instantiating settings for global access
settings = Settings()