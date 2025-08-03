import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        logger.info(f"Новый пользователь: {user.id}")
        await update.message.reply_text(f"🎉 Привет, {user.first_name}! Я работаю!")
    except Exception as e:
        logger.error(f"Ошибка в /start: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}")

def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        logger.error("Токен не найден!")
        return

    try:
        app = Application.builder().token(TOKEN).build()
        
        # Регистрация обработчиков
        app.add_handler(CommandHandler("start", start))
        app.add_error_handler(error_handler)
        
        # Логирование всех сообщений
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, 
            lambda u, c: logger.info(f"Получено сообщение: {u.message.text}")))
        
        logger.info("Бот запущен и готов к работе")
        app.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
    except Exception as e:
        logger.critical(f"Фатальная ошибка: {e}")

if __name__ == "__main__":
    main()