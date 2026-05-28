import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from services.nlp_service import NLPService
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

    def __init__(self, nlp_service: NLPService):
        self.nlp_service = nlp_service
        # Initialize the Telegram application with your token
        self.app = Application.builder().token(settings.TELEGRAM_TOKEN).build()
        
        # Listen for any text message that is NOT a command (like /start)
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processes incoming messages asynchronously."""
        user_message = update.message.text
        
        # 1. Give immediate feedback to the user
        await update.message.reply_text("⏳ Processing transaction...")
        
        try:
            # 2. Extract structured data using Gemini
            transaction = self.nlp_service.message_processor(user_message)
            
            # 3. TODO: Send 'transaction' to Google Sheets Service here
            
            # 4. Format a clean response
            response = (
                "✅ **Transaction parsed successfully**\n\n"
                f"🔹 **Type:** {transaction.transaction_type}\n"
                f"💰 **Amount:** ${transaction.amount}\n"
                f"🏷️ **Category:** {transaction.category}\n"
                f"📝 **Description:** {transaction.description}\n"
                f"🏦 **Origin:** {transaction.source_account or 'N/A'}\n"
                f"🎯 **Destination:** {transaction.destination_account or 'N/A'}\n"
                f"📅 **Date:** {transaction.date}"
            )
            
            # Send the final confirmation using Markdown formatting
            await update.message.reply_text(response, parse_mode="Markdown")
            
        except Exception as e:
            logging.error(f"Error processing message: {e}")
            await update.message.reply_text("❌ Sorry, I couldn't process that. Try being more specific.")

    def run(self):
        """Starts the bot in polling mode."""
        print("🤖 Bot is running! Send a message from Telegram...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)