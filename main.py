from collections import deque
from contextlib import asynccontextmanager
from http import HTTPStatus
import logging

from fastapi import BackgroundTasks, FastAPI, Request, Response
from telegram import Update

from core.config import settings
from core.database.session import SessionLocal, init_db
from repositories.user_repository import UserRepository
from repositories.transaction_repository import TransactionRepository
from services.nlp_service import NLPService
from services.sheets_service import SheetsService
from services.ingestion_service import TransactionIngestionService
from services.telegram_bot import TelegramBot

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# 1. Global database and services instantiation
init_db()
db_session = SessionLocal()
user_repository = UserRepository(db=db_session)
transaction_repository = TransactionRepository(db=db_session)

nlp_service = NLPService()
sheets_service = None
if settings.ENABLE_GOOGLE_SHEETS_SYNC:
    try:
        sheets_service = SheetsService(spreadsheet_name="Finanzas personales")
        logging.info("Google Sheets synchronization is ENABLED.")
    except Exception as exc:
        logging.warning(f"Could not initialize SheetsService, continuing in DB-only mode: {exc}")
        sheets_service = None
else:
    logging.info("Google Sheets real-time sync is DISABLED. Using database as single source of truth.")

ingestion_service = TransactionIngestionService(
    transaction_repository=transaction_repository,
    sheets_service=sheets_service,
)
bot = TelegramBot(
    nlp_service=nlp_service,
    sheets_service=sheets_service,
    ingestion_service=ingestion_service,
    user_repository=user_repository,
    transaction_repository=transaction_repository,
)

# Cache to track processed updates and prevent Telegram retry duplicates
MAX_PROCESSED_UPDATES = 2000
processed_update_ids = set()
update_id_queue = deque()


def is_duplicate_update(update_id: int) -> bool:
    """Checks if an update_id was already handled recently to prevent duplicate executions."""
    if update_id in processed_update_ids:
        return True
    processed_update_ids.add(update_id)
    update_id_queue.append(update_id)
    if len(update_id_queue) > MAX_PROCESSED_UPDATES:
        oldest_id = update_id_queue.popleft()
        processed_update_ids.discard(oldest_id)
    return False


async def process_update_in_background(update: Update):
    """Processes the Telegram update asynchronously without blocking webhook responses."""
    try:
        await bot.app.process_update(update)
    except Exception as exc:
        logging.error(f"Error handling update {update.update_id}: {exc}")


# 2. Application lifecycle management (Start/Stop)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # On server startup: Initialize Telegram bot
    await bot.app.initialize()
    await bot.app.start()

    # Configure Webhook if in Production (Render)
    webhook_url = settings.WEBHOOK_URL
    if webhook_url:
        await bot.app.bot.set_webhook(url=f"{webhook_url}/webhook")
        logging.info(f"Webhook set to: {webhook_url}/webhook")

    yield

    # On server shutdown: Cleanup
    await bot.app.stop()
    await bot.app.shutdown()


# 3. FastAPI application creation
app = FastAPI(lifespan=lifespan)


@app.post("/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook endpoint where Telegram delivers updates.
    Returns 200 OK immediately and processes updates in background tasks
    to prevent Telegram retry timeouts on long operations.
    """
    data = await request.json()
    update = Update.de_json(data, bot.app.bot)

    if update and update.update_id:
        if is_duplicate_update(update.update_id):
            logging.info(f"Duplicate update {update.update_id} dropped.")
            return Response(status_code=HTTPStatus.OK)

        background_tasks.add_task(process_update_in_background, update)

    return Response(status_code=HTTPStatus.OK)


@app.get("/")
def health_check():
    """Health check endpoint to verify server is active."""
    return {"status": "🤖 El bot está vivo y listo para recibir finanzas."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)