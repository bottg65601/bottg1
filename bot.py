import os
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получение токена из переменных окружения
TOKEN = os.getenv("TOKEN")  # Более понятное имя переменной

def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    logger.info(f"User {user.id} started the bot")
    update.message.reply_text(f"Привет, {user.first_name}! Я бот на fly.io!")

def echo(update: Update, context: CallbackContext) -> None:
    """Эхо-ответ на текстовые сообщения"""
    logger.info(f"Echo message from {update.effective_user.id}: {update.message.text}")
    update.message.reply_text(update.message.text)

def error_handler(update: Update, context: CallbackContext) -> None:
    """Обработчик ошибок"""
    logger.error(f'Update {update} caused error {context.error}')

def main() -> None:
    """Основная функция запуска бота"""
    try:
        # Инициализация бота
        updater = Updater(TOKEN)
        dispatcher = updater.dispatcher

        # Регистрация обработчиков
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
        
        # Обработчик ошибок
        dispatcher.add_error_handler(error_handler)

        # Запуск бота
        logger.info("Starting bot...")
        updater.start_polling()
        
        # Информационное сообщение
        logger.info("Bot is running and waiting for messages...")
        
        # Бесконечный цикл для поддержания работы
        updater.idle()

    except Exception as e:
        logger.critical(f"Bot crashed with error: {e}")
        raise

if __name__ == "__main__":
    main()