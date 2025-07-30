import os
import logging
import uvloop
from telegram.ext import Application, CommandHandler

# Настройка uvloop для asyncio
uvloop.install()

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update, context):
    """Обработчик команды /start"""
    await update.message.reply_text("🛠️ Бот работает на Fly.io!")

async def post_init(application):
    """Действия после инициализации"""
    logger.info("Бот успешно инициализирован")

def main():
    try:
        # Создаем Application с настройками для Fly.io
        application = Application.builder() \
            .token(os.getenv("TELEGRAM_TOKEN")) \
            .post_init(post_init) \
            .build()

        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start))

        # Запускаем бота
        logger.info("Запуск бота в режиме polling...")
        application.run_polling(
            close_loop=False,  # Важно для Fly.io!
            drop_pending_updates=True
        )

    except Exception as e:
        logger.critical(f"Ошибка: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()