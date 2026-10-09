import logging
import os
import uuid
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from services.nlp_service import NLPService
from services.sheets_service import SheetsService
from core.config import settings

# Logging configuration to see background errors in the terminal
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

class TelegramBot:
    """
    Handles the Telegram interface, receiving user messages and orchestrating 
    the NLP processing and database storage.
    """

    def __init__(self, nlp_service: NLPService, sheets_service: SheetsService):
        self.nlp_service = nlp_service
        self.sheets_service = sheets_service
        self.app = Application.builder().token(settings.TELEGRAM_TOKEN).build()
        
        # Listen for any text message that is NOT a command (like /start)
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        # Listen for voice notes
        self.app.add_handler(MessageHandler(filters.VOICE, self.handle_voice))
        # Listen for documents (PDF, CSV, Excel)
        self.app.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))

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
        """Processes incoming messages asynchronously."""
        user_message = update.message.text
        await update.message.reply_text("⏳ Procesando transacción...")
        
        try:
            transaction = self.nlp_service.message_processor(user_message)
            added = self.sheets_service.append_transaction(transaction)
            
            if added:
                response = f"✅ **Transacción guardada exitosamente**\n\n{self._format_transaction_response(transaction)}"
            else:
                response = f"⚠️ **Transacción duplicada ignorada**\n\nYa habías registrado algo idéntico:\n{self._format_transaction_response(transaction)}"
                
            await update.message.reply_text(response, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Error processing message: {e}")
            await update.message.reply_text("❌ Lo siento, no pude procesar eso. Intenta ser más específico.")

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processes voice notes."""
        await update.message.reply_text("🎙️ Escuchando y procesando tu audio...")
        
        try:
            voice = update.message.voice
            file = await context.bot.get_file(voice.file_id)
            
            # Guardamos temporalmente el audio
            file_path = f"temp_audio_{uuid.uuid4()}.ogg"
            await file.download_to_drive(file_path)
            
            # Lo mandamos a procesar a Gemini
            transaction = self.nlp_service.process_audio(file_path)
            
            # Borramos el archivo local
            if os.path.exists(file_path):
                os.remove(file_path)
                
            added = self.sheets_service.append_transaction(transaction)
            
            if added:
                response = f"✅ **Audio procesado y guardado**\n\n{self._format_transaction_response(transaction)}"
            else:
                response = f"⚠️ **Transacción duplicada (desde audio)**\n\nYa existía este registro:\n{self._format_transaction_response(transaction)}"
                
            await update.message.reply_text(response, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Error processing voice: {e}")
            await update.message.reply_text("❌ Hubo un error al entender tu nota de voz.")

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processes document uploads (PDFs, Excels, CSVs)."""
        await update.message.reply_text("📄 Analizando el documento, esto puede tomar unos segundos...")
        
        try:
            document = update.message.document
            file = await context.bot.get_file(document.file_id)
            
            # Guardamos temporalmente el documento
            ext = os.path.splitext(document.file_name)[1]
            file_path = f"temp_doc_{uuid.uuid4()}{ext}"
            await file.download_to_drive(file_path)
            
            # Procesamos con Gemini para extraer múltiples transacciones
            transactions = self.nlp_service.process_document(file_path)
            
            # Borramos el archivo local
            if os.path.exists(file_path):
                os.remove(file_path)
                
            if not transactions:
                await update.message.reply_text("⚠️ No encontré ninguna transacción válida en este documento.")
                return
                
            # Guardamos en bloque
            added_count, duplicate_count = self.sheets_service.append_transactions(transactions)
            
            response = "✅ **Documento procesado con éxito**\n\n"
            response += "📊 **Resumen:**\n"
            response += f"- ➕ {added_count} transacciones nuevas guardadas.\n"
            response += f"- ⏭️ {duplicate_count} transacciones ignoradas por ser duplicadas."
            
            await update.message.reply_text(response, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Error processing document: {e}")
            await update.message.reply_text("❌ Hubo un error al procesar el archivo. Asegúrate de que sea un estado de cuenta legible.")