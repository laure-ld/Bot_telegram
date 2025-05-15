import os
import atexit
from app import routes, bot_handlers, scheduler
from app.config import TELEGRAM_TOKEN
from app.database import connect_db
from app.routes import app
from telegram import Bot

bot = Bot(token=TELEGRAM_TOKEN)

def main():
    connect_db()
    scheduler.start()

    # Configure webhook si besoin
    url = f"https://veille-techno-bot.onrender.com/{TELEGRAM_TOKEN}"
    bot.delete_webhook()
    bot.set_webhook(url)

    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

if __name__ == '__main__':
    main()
