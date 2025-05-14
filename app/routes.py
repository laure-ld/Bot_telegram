from flask import Flask, request
from telegram import Update
from app import dispatcher, bot, TELEGRAM_TOKEN

app = Flask(__name__)

@app.route('/')
def index():
    return "✅ Bot is running."

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"
