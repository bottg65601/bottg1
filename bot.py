import os
import logging
from telegram import Update, Bot
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    Dispatcher
)

# ===== Конфигурация логирования =====
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),  # Вывод в консоль
        logging.FileHandler('bot.log')  # Запись в файл
    ]
)
logger = logging.getLogger(__name__)

# ===== Конфигурация бота =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")  # Безопасное получение токена

if not TELEGRAM_TOKEN:
    logger.critical("Токен бота не найден! Установите через flyctl secrets set TELEGRAM_TOKEN=ваш_токен")
    raise ValueError("Токен бота не указан")

# ===== Обработчики сообщений =====
async def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start с асинхронной поддержкой"""
    user = update.effective_user
    logger.info(f"Новый пользователь: {user.full_name} (ID: {user.id})")
    await update.message.reply_html(
        f"Привет, {user.mention_html()}!\n"
        "Я работаю на платформе fly.io 🚀"
    )

async def echo(update: Update, context: CallbackContext) -> None:
    """Асинхронный эхо-ответ"""
    logger.info(f"Сообщение от {update.effective_user.id}: {update.message.text}")
    await update.message.reply_text(update.message.text)

async def error_handler(update: Update, context: CallbackContext) -> None:
    """Улучшенный обработчик ошибок"""
    logger.error(f'Ошибка: {context.error}', exc_info=True)
    if update and update.effective_chat:
        await update.effective_chat.send_message(
            "⚠️ Произошла ошибка при обработке вашего запроса. "
            "Разработчик уже уведомлен."
        )

# ===== Основная функция =====
def main() -> None:
    try:
        logger.info("Инициализация бота...")
        
        # Инициализация с использованием async
        bot = Bot(TELEGRAM_TOKEN)
        dispatcher = Dispatcher(bot=bot, update_queue=None, workers=4)
        
        # Регистрация обработчиков
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(MessageHandler(
            Filters.text & ~Filters.command, echo
        ))
        dispatcher.add_error_handler(error_handler)
        
        # Запуск бота
        updater = Updater(bot=bot, dispatcher=dispatcher)
        updater.start_polling(
            drop_pending_updates=True,  # Игнорировать старые сообщения
            timeout=30,  # Таймаут соединения
            read_latency=2.0  # Задержка чтения
        )
        
        logger.info("Бот успешно запущен и ожидает сообщений...")
        updater.idle()

    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()