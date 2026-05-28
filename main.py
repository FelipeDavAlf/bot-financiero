import os
from fastapi import FastAPI, Request
from telegram import Update
import uvicorn
from contextlib import asynccontextmanager

from services.nlp_service import NLPService
from services.sheets_service import SheetsService
from services.telegram_bot import TelegramBot
from core.config import settings

# 1. Instanciamos los servicios globales
nlp_service = NLPService()
# OJO: Asegúrate de que el nombre coincida exactamente con tu Excel
sheets_service = SheetsService(spreadsheet_name="Finanzas personales")
bot = TelegramBot(nlp_service=nlp_service, sheets_service=sheets_service)

# 2. Manejo del ciclo de vida de la aplicación (Start/Stop)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Al arrancar el servidor: Inicializamos el bot de Telegram
    await bot.app.initialize()
    await bot.app.start()
    
    # Configuramos el Webhook si estamos en Producción (Render)
    webhook_url = settings.WEBHOOK_URL
    if webhook_url:
        # Le decimos a Telegram: "Cuando haya mensajes, mándalos a esta URL"
        await bot.app.bot.set_webhook(url=f"{webhook_url}/webhook")
        print(f"✅ Webhook configurado en: {webhook_url}/webhook")
    
    yield # Aquí la aplicación se queda corriendo
    
    # Al apagar el servidor: Limpieza
    await bot.app.stop()
    await bot.app.shutdown()

# 3. Creamos la API de FastAPI
app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Este endpoint es la puerta donde Telegram entregará los mensajes."""
    data = await request.json()
    # Convertimos el JSON de Telegram al objeto Update que nuestro bot entiende
    update = Update.de_json(data, bot.app.bot)
    # Lo pasamos por nuestra lógica
    await bot.app.process_update(update)
    return {"status": "ok"}

@app.get("/")
def health_check():
    """Un endpoint de prueba para saber que el servidor no se ha caído."""
    return {"status": "🤖 El bot está vivo y listo para recibir finanzas."}