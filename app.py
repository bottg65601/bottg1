from flask import Flask, request
from telegram.ext import Application, CommandHandler
import os

app = Flask(__name__)
bot = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()

async def start(update, context):
    await update.message.reply_text("Bot is working!")

bot.add_handler(CommandHandler("start", start))

@app.route('/webhook', methods=['POST'])
async def webhook():
    update = Update.de_json(request.json, bot.bot)
    await bot.process_update(update)
    return '', 200

if __name__ == '__main__':
    bot.run_webhook(
        listen="0.0.0.0",
        port=8080,
        webhook_url="https://bottg1.fly.dev/webhook"
    )