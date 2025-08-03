import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    await update.message.reply_text(f"🚀 Бот запущен! Привет, {user.first_name}!")

def main():
    # Получаем токен из переменных окружения
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        raise ValueError("Не задан TELEGRAM_TOKEN!")
    
    # Создаем приложение
    app = Application.builder().token(TOKEN).build()
    
    # Регистрируем обработчики команд
    app.add_handler(CommandHandler("start", start))
    
    # Запускаем бота
    logger.info("Бот запускается...")
    app.run_polling()

if __name__ == "__main__":
    main()