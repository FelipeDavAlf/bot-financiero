from services.nlp_service import NLPService
from services.telegram_bot import TelegramBot

def main():
    # Initialize the Artificial Intelligence service
    nlp_service = NLPService()
    
    # Initialize the Telegram bot, injecting the NLP service (Dependency Injection)
    bot = TelegramBot(nlp_service=nlp_service)
    
    # Start the bot
    bot.run()

if __name__ == "__main__":
    main()