import asyncio
from datetime import datetime
from enum import Enum
import logging
import os
from typing import Optional
import uuid
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from services.nlp_service import NLPService
from services.sheets_service import SheetsService
from services.ingestion_service import TransactionIngestionService
from services.export_service import ExcelExportService
from repositories.user_repository import UserRepository
from repositories.transaction_repository import TransactionRepository
from services.bot_messages import (
    WELCOME_MESSAGE,
    HELP_MESSAGE,
    ACCOUNTS_MESSAGE,
    CATEGORIES_MESSAGE,
    NON_TRANSACTION_FALLBACK_MESSAGE,
    is_greeting_or_help_intent,
)
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
    DocumentProcessingState.SAVING: "📊 **Guardando registros:** Guardando en tu base de datos...",
}


class TelegramBot:
    """
    Handles the Telegram interface, receiving user messages and orchestrating 
    the NLP processing and database storage via the modular Ingestion Service.
    """

    def __init__(
        self,
        nlp_service: NLPService,
        sheets_service: Optional[SheetsService] = None,
        ingestion_service: Optional[TransactionIngestionService] = None,
        user_repository: Optional[UserRepository] = None,
        transaction_repository: Optional[TransactionRepository] = None,
        export_service: Optional[ExcelExportService] = None,
    ):
        self.nlp_service = nlp_service
        self.sheets_service = sheets_service
        self.user_repository = user_repository
        self.transaction_repository = transaction_repository
        self.export_service = export_service or ExcelExportService()
        self.ingestion_service = ingestion_service or TransactionIngestionService(
            sheets_service=sheets_service
        )
        self.app = (
            Application.builder()
            .token(settings.TELEGRAM_TOKEN)
            .read_timeout(30)
            .write_timeout(30)
            .connect_timeout(30)
            .build()
        )
        
        # Command handlers for welcome, help, accounts, categories and export
        self.app.add_handler(CommandHandler("start", self.handle_start))
        self.app.add_handler(CommandHandler("help", self.handle_help))
        self.app.add_handler(CommandHandler("cuentas", self.handle_cuentas))
        self.app.add_handler(CommandHandler("categorias", self.handle_categorias))
        self.app.add_handler(CommandHandler("exportar", self.handle_exportar))
        self.app.add_handler(CommandHandler("descargar", self.handle_exportar))
        
        # Listen for any text message that is NOT a command (like /start)
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        # Listen for voice notes
        self.app.add_handler(MessageHandler(filters.VOICE, self.handle_voice))
        # Listen for documents (PDF, CSV, Excel)
        self.app.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))

    def _get_or_create_user(self, update: Update):
        """Retrieves or registers the Telegram user in the database."""
        if not self.user_repository or not update.effective_user:
            return None
        return self.user_repository.get_or_create_user(
            telegram_id=update.effective_user.id,
            first_name=update.effective_user.first_name,
            username=update.effective_user.username,
        )

    async def _update_status(self, message, text: str):
        """Safely updates a Telegram status message."""
        try:
            await message.edit_text(text, parse_mode="Markdown")
        except Exception as exc:
            logging.debug(f"Could not edit status message: {exc}")

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Sends the detailed welcome message and registers the user."""
        self._get_or_create_user(update)
        await update.message.reply_text(WELCOME_MESSAGE, parse_mode="Markdown")

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Sends the usage guide and examples."""
        await update.message.reply_text(HELP_MESSAGE, parse_mode="Markdown")

    async def handle_cuentas(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Sends the list of supported accounts and payment methods."""
        user = self._get_or_create_user(update)
        if self.user_repository and user:
            accounts = self.user_repository.get_user_accounts(user.id)
            if accounts:
                accounts_text = "💳 **Tus Cuentas y Métodos de Pago Disponibles:**\n\n"
                for acc in accounts:
                    accounts_text += f"• 🔹 **{acc.name}** ({acc.account_type})\n"
                accounts_text += "\n💡 *Puedes registrar gastos indicando cualquiera de estas cuentas.*"
                await update.message.reply_text(accounts_text, parse_mode="Markdown")
                return

        await update.message.reply_text(ACCOUNTS_MESSAGE, parse_mode="Markdown")

    async def handle_categorias(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Sends the list of supported categories."""
        await update.message.reply_text(CATEGORIES_MESSAGE, parse_mode="Markdown")

    async def handle_exportar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generates and sends an Excel workbook containing financial summary and history."""
        user = self._get_or_create_user(update)
        if not user or not self.transaction_repository:
            await update.message.reply_text("❌ No fue posible acceder a tu historial financiero.")
            return

        transactions = await asyncio.to_thread(
            self.transaction_repository.get_all_user_transactions,
            user.id,
        )
        if not transactions:
            await update.message.reply_text(
                "ℹ️ **Aún no tienes movimientos registrados.**\n\n"
                "Comienza registrando tus gastos o ingresos (por texto, audio o estado de cuenta) "
                "y luego usa `/exportar` para descargar tu reporte en Excel.",
                parse_mode="Markdown",
            )
            return

        chat_id = update.effective_chat.id
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)
        status_message = await update.message.reply_text("⏳ **Generando tu reporte en Excel...**", parse_mode="Markdown")

        try:
            excel_buffer = await asyncio.to_thread(
                self.export_service.generate_user_finance_workbook,
                user_name=user.first_name or user.username or "Usuario",
                transactions=transactions,
            )

            today_str = datetime.now().strftime("%Y-%m-%d")
            filename = f"Finanzas_{today_str}.xlsx"

            caption = (
                f"📊 **¡Aquí tienes tu Reporte Financiero!**\n\n"
                f"👤 **Usuario:** {user.first_name or user.username or 'Usuario'}\n"
                f"📝 **Transacciones incluidas:** {len(transactions)}\n"
                f"📅 **Corte al:** {today_str}\n\n"
                f"✨ *Contiene 2 pestañas:* Resumen Financiero (balances y categorías) y Detalle de Movimientos."
            )

            await update.message.reply_document(
                document=excel_buffer,
                filename=filename,
                caption=caption,
                parse_mode="Markdown",
            )
            try:
                await status_message.delete()
            except Exception:
                pass
        except Exception as exc:
            logging.error(f"Error generating or sending Excel report: {exc}", exc_info=True)
            await self._update_status(
                status_message,
                "❌ Ocurrió un error al generar tu archivo Excel. Por favor intenta de nuevo en unos momentos."
            )


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

        # Fast recognition for greetings and general information requests
        if is_greeting_or_help_intent(user_message):
            await update.message.reply_text(WELCOME_MESSAGE, parse_mode="Markdown")
            return

        user = self._get_or_create_user(update)
        user_id = user.id if user else None
        user_accounts = (
            self.user_repository.get_user_account_names(user.id)
            if (self.user_repository and user)
            else None
        )

        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        status_message = await update.message.reply_text("⏳ Procesando transacción...")
        
        try:
            transaction = await asyncio.to_thread(
                self.nlp_service.message_processor,
                user_message,
                user_accounts,
            )
            if not transaction:
                await self._update_status(status_message, NON_TRANSACTION_FALLBACK_MESSAGE)
                return

            ingestion_result = await asyncio.to_thread(
                self.ingestion_service.ingest_transaction,
                transaction,
                user_id,
            )
            
            if ingestion_result.success:
                response = f"✅ **Transacción guardada exitosamente**\n\n{self._format_transaction_response(transaction)}"
            elif ingestion_result.is_duplicate:
                response = f"⚠️ **Transacción duplicada ignorada**\n\nYa habías registrado algo idéntico:\n{self._format_transaction_response(transaction)}"
            else:
                response = f"❌ {ingestion_result.error_message or 'Error al procesar la transacción.'}"
                
            await self._update_status(status_message, response)
        except Exception as e:
            logging.error(f"Error processing message: {e}", exc_info=True)
            await self._update_status(
                status_message,
                "❌ Ocurrió un error al procesar tu solicitud. Por favor intenta de nuevo en unos momentos."
            )

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processes voice notes with progressive status updates."""
        chat_id = update.effective_chat.id
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        status_message = await update.message.reply_text("🎙️ **Escuchando nota de voz:** Recibiendo audio...", parse_mode="Markdown")
        file_path = None
        
        user = self._get_or_create_user(update)
        user_id = user.id if user else None
        user_accounts = (
            self.user_repository.get_user_account_names(user.id)
            if (self.user_repository and user)
            else None
        )

        try:
            voice = update.message.voice
            file = await context.bot.get_file(voice.file_id)
            
            # Temporarily save voice note
            file_path = f"temp_audio_{uuid.uuid4()}.ogg"
            await file.download_to_drive(file_path)
            
            await self._update_status(status_message, "🤖 **Analizando audio:** Interpretando transacción con Gemini...")
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            
            transaction = await asyncio.to_thread(self.nlp_service.process_audio, file_path, user_accounts)
            if not transaction:
                await self._update_status(
                    status_message,
                    "🤔 No identifiqué ninguna transacción financiera en tu nota de voz. Por favor intenta grabar de nuevo mencionando el monto y el concepto claramente (ej. 'Gasté 80 pesos en comida')."
                )
                return
            
            await self._update_status(status_message, "📊 **Guardando transacción:** Sincronizando registros...")
            ingestion_result = await asyncio.to_thread(self.ingestion_service.ingest_transaction, transaction, user_id)
            
            if ingestion_result.success:
                response = f"✅ **Audio procesado y guardado**\n\n{self._format_transaction_response(transaction)}"
            elif ingestion_result.is_duplicate:
                response = f"⚠️ **Transacción duplicada (desde audio)**\n\nYa existía este registro:\n{self._format_transaction_response(transaction)}"
            else:
                response = f"❌ {ingestion_result.error_message or 'Error al procesar el audio.'}"
                
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
        
        user = self._get_or_create_user(update)
        user_id = user.id if user else None

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
                
            # State: Saving transactions
            await self._update_status(
                status_message,
                DOCUMENT_STATE_MESSAGES[DocumentProcessingState.SAVING]
            )
            batch_result = await asyncio.to_thread(self.ingestion_service.ingest_batch, transactions, user_id)
            
            response = "✅ **Documento procesado con éxito**\n\n"
            response += "📊 **Resumen:**\n"
            response += f"- ➕ {batch_result.added_count} transacciones nuevas guardadas.\n"
            response += f"- ⏭️ {batch_result.duplicate_count} transacciones ignoradas por ser duplicadas."
            if batch_result.invalid_count > 0:
                response += f"\n- ⚠️ {batch_result.invalid_count} transacciones descartadas por datos incompletos o erróneos."
            
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