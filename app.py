import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Инициализация бота
bot_app = Application.builder().token(TELEGRAM_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Бот работает!")

# Регистрация обработчиков
bot_app.add_handler(CommandHandler("start", start))

@app.route('/')
def health_check():
    return "OK", 200

@app.route('/webhook', methods=['POST'])
async def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = Update.de_json(request.get_json(force=True), bot_app.bot)
        await bot_app.process_update(update)
    return '', 200

def run():
    # Запускаем вебхук в отдельном потоке
    from threading import Thread
    Thread(target=lambda: bot_app.run_webhook(
        listen="0.0.0.0",
        port=8080,
        webhook_url="https://bottg1.fly.dev/webhook",
        drop_pending_updates=True
    )).start()
    
    # Запускаем Flask
    app.run(host='0.0.0.0', port=8081)

if __name__ == '__main__':
    run()