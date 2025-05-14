import os

DATABASE_URL = os.getenv("DATABASE_URL")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
NEWS_API_TOKEN = os.getenv("NEWS_API_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
NEWS_API_URL = "https://newsapi.org/v2/everything"