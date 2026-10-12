import asyncio
from enum import Enum
import logging
import os
import uuid
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from services.nlp_service import NLPService
from services.sheets_service import SheetsService
from core.config import settings

# Logging configuration to see background errors in the terminal
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


class DocumentProcessingState(str, Enum):
    """Represents the sequential states of document processing."""
    DOWNLOADING = "DOWNLOADING"
    EXTRACTING = "EXTRACTING"
    ANALYZING = "ANALYZING"
    SAVING = "SAVING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


DOCUMENT_STATE_MESSAGES = {
    DocumentProcessingState.DOWNLOADING: "📥 **Descargando documento:** Recibiendo archivo...",
    DocumentProcessingState.EXTRACTING: "🔍 **Extrayendo datos:** Leyendo tablas y formato del archivo...",
    DocumentProcessingState.ANALYZING: "🤖 **Analizando con IA:** Detectando y clasificando transacciones con Gemini...",
    DocumentProcessingState.SAVING: "📊 **Guardando registros:** Sincronizando con Google Sheets...",
}


class TelegramBot:
    """
    Handles the Telegram interface, receiving user messages and orchestrating 
    the NLP processing and database storage.
    """

    def __init__(self, nlp_service: NLPService, sheets_service: SheetsService):
        self.nlp_service = nlp_service
        self.sheets_service = sheets_service
        self.app = (
            Application.builder()
            .token(settings.TELEGRAM_TOKEN)
            .read_timeout(30)
            .write_timeout(30)
            .connect_timeout(30)
            .build()
        )
        
        # Listen for any text message that is NOT a command (like /start)
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        # Listen for voice notes
        self.app.add_handler(MessageHandler(filters.VOICE, self.handle_voice))
        # Listen for documents (PDF, CSV, Excel)
        self.app.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))

    async def _update_status(self, message, text: str):
        """Safely updates a Telegram status message."""
        try:
            await message.edit_text(text, parse_mode="Markdown")
        except Exception as exc:
            logging.debug(f"Could not edit status message: {exc}")

    def _format_transaction_response(self, transaction) -> str:
        return (
            f"🔹 **Tipo:** {transaction.transaction_type}\n"
            f"💰 **Monto:** ${transaction.amount}\n"
            f"🏷️ **Categoría:** {transaction.category}\n"
            f"📌 **Subcategoría:** {transaction.subcategory}\n"
            f"📝 **Descripción:** {transaction.description}\n"
            f"🏦 **Origen:** {transaction.source_account or 'N/A'}\n"
            f"🎯 **Destino:** {transaction.destination_account or 'N/A'}\n"
            f"📅 **Fecha:** {transaction.date}"
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processes incoming text messages asynchronously."""
        user_message = update.message.text
        chat_id = update.effective_chat.id
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        status_message = await update.message.reply_text("⏳ Procesando transacción...")
        
        try:
            transaction = await asyncio.to_thread(self.nlp_service.message_processor, user_message)
            added = await asyncio.to_thread(self.sheets_service.append_transaction, transaction)
            
            if added:
                response = f"✅ **Transacción guardada exitosamente**\n\n{self._format_transaction_response(transaction)}"
            else:
                response = f"⚠️ **Transacción duplicada ignorada**\n\nYa habías registrado algo idéntico:\n{self._format_transaction_response(transaction)}"
                
            await self._update_status(status_message, response)
        except Exception as e:
            logging.error(f"Error processing message: {e}")
            await self._update_status(status_message, "❌ Lo siento, no pude procesar eso. Intenta ser más específico.")

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processes voice notes with progressive status updates."""
        chat_id = update.effective_chat.id
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        status_message = await update.message.reply_text("🎙️ **Escuchando nota de voz:** Recibiendo audio...", parse_mode="Markdown")
        file_path = None
        
        try:
            voice = update.message.voice
            file = await context.bot.get_file(voice.file_id)
            
            # Temporarily save voice note
            file_path = f"temp_audio_{uuid.uuid4()}.ogg"
            await file.download_to_drive(file_path)
            
            await self._update_status(status_message, "🤖 **Analizando audio:** Interpretando transacción con Gemini...")
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            
            transaction = await asyncio.to_thread(self.nlp_service.process_audio, file_path)
            
            await self._update_status(status_message, "📊 **Guardando transacción:** Sincronizando con Google Sheets...")
            added = await asyncio.to_thread(self.sheets_service.append_transaction, transaction)
            
            if added:
                response = f"✅ **Audio procesado y guardado**\n\n{self._format_transaction_response(transaction)}"
            else:
                response = f"⚠️ **Transacción duplicada (desde audio)**\n\nYa existía este registro:\n{self._format_transaction_response(transaction)}"
                
            await self._update_status(status_message, response)
        except Exception as e:
            logging.error(f"Error processing voice: {e}")
            await self._update_status(status_message, "❌ Hubo un error al entender tu nota de voz.")
        finally:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processes document uploads (PDFs, Excels, CSVs) with live state tracking."""
        chat_id = update.effective_chat.id
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        
        status_message = await update.message.reply_text(
            DOCUMENT_STATE_MESSAGES[DocumentProcessingState.DOWNLOADING],
            parse_mode="Markdown"
        )
        file_path = None
        
        try:
            document = update.message.document
            file = await context.bot.get_file(document.file_id)
            
            # Temporarily save document
            ext = os.path.splitext(document.file_name)[1]
            file_path = f"temp_doc_{uuid.uuid4()}{ext}"
            await file.download_to_drive(file_path)
            
            # State: Extracting tabular content
            await self._update_status(
                status_message,
                DOCUMENT_STATE_MESSAGES[DocumentProcessingState.EXTRACTING]
            )
            extracted_text = await asyncio.to_thread(self.nlp_service.extract_document_text, file_path)
            
            # State: Analyzing with AI
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await self._update_status(
                status_message,
                DOCUMENT_STATE_MESSAGES[DocumentProcessingState.ANALYZING]
            )
            transactions = await asyncio.to_thread(self.nlp_service.parse_transactions_from_text, extracted_text)
            
            if not transactions:
                await self._update_status(status_message, "⚠️ No encontré ninguna transacción válida en este documento.")
                return
                
            # State: Saving to Google Sheets
            await self._update_status(
                status_message,
                DOCUMENT_STATE_MESSAGES[DocumentProcessingState.SAVING]
            )
            added_count, duplicate_count = await asyncio.to_thread(self.sheets_service.append_transactions, transactions)
            
            response = "✅ **Documento procesado con éxito**\n\n"
            response += "📊 **Resumen:**\n"
            response += f"- ➕ {added_count} transacciones nuevas guardadas.\n"
            response += f"- ⏭️ {duplicate_count} transacciones ignoradas por ser duplicadas."
            
            await self._update_status(status_message, response)
        except Exception as e:
            logging.error(f"Error processing document: {e}")
            await self._update_status(
                status_message,
                "❌ Hubo un error al procesar el archivo. Asegúrate de que sea un estado de cuenta legible."
            )
        finally:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass