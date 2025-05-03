import os
import requests
import pytz
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
NEWS_API_TOKEN = os.getenv("NEWS_API_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
NEWSAPI_URL = "https://newsapi.org/v2/everything"

timezone = pytz.timezone('Europe/Paris')
scheduler = BackgroundScheduler(timezone=timezone)
bot = Bot(token=TELEGRAM_TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot=bot, update_queue=None, workers=4, use_context=True)

# === Commandes ===
def scheduler_daily():
    keywords = ["Technology", "Artificial Intelligence", "New technology"]
    full_message = "👋 Hello ! Voici les news du jour:\n"
    
    for keyword in keywords:
        params = {
            "apiKey": NEWS_API_TOKEN,
            "q": keyword,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 3
        }
        try:
            response = requests.get(NEWSAPI_URL, params=params)
            data = response.json()
            articles = data.get("articles", [])

            if articles: 
                full_message += f"\n📰 *{keyword}* :\n\n"
                
                for i, article in enumerate(articles, 1):
                    title = article.get("title", "sans titre")
                    url = article.get("url", "#")
                    source = article.get("source", {}).get("name", "source inconnue")
                    full_message += f"{i}. [{title}]({url})\n   Source: {source}\n\n"
            
            else:
                Update.message.reply_text(f"Aucun article trouvé.")
                return
        except Exception as e:
                full_message += f"Erreur lors de la récupération des actualités {keyword}: {e}\n"

    bot.send_message(chat_id=CHAT_ID, text=full_message, parse_mode="Markdown", disable_web_page_preview=True)
scheduler.add_job(scheduler_daily, 'cron', hour=9, minute=00)
scheduler.start()

def search_news(update, context):
    if not context.args:
        update.message.reply_text("Utilisation : /search <mot-clé>")
        return

    query = " ".join(context.args)
    try:
        params = {
            "apiKey": NEWS_API_TOKEN,
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 3
        }
        response = requests.get(NEWSAPI_URL, params=params)

        if response.status_code == 200:
            data = response.json()
            articles = data.get("articles", [])

            if not articles:
                update.message.reply_text(f"Aucun article trouvé pour : {query}")
                return

            message = f"🔍 Résultats pour : *{query}*\n\n"
            for i, article in enumerate(articles, 1):
                title = article.get("title", "Sans titre")
                url = article.get("url", "#")
                source = article.get("source", {}).get("name", "Source inconnue")
                message += f"{i}. [{title}]({url})\n   Source: {source}\n\n"

            update.message.reply_text(message, parse_mode="Markdown", disable_web_page_preview=True)

        else:
            update.message.reply_text(f"Erreur : {response.status_code}")
    except Exception as e:
        update.message.reply_text(f"Une erreur est survenue : {e}")


def start(update, context):
    update.message.reply_text("👋 Bienvenue dans le bot de veille techno ! Tape /help pour voir les commandes.")

def help_command(update, context):
    update.message.reply_text(
        "📚 Commandes disponibles :\n"
        "/python - Actualités python\n"
        "/js - Actualités javaScript\n"
        "/ai - Actualités intelligence artificielle\n"
        "/cyber - Actualités cybersécurité\n"
        "/react - Actualités react\n"
        "/cloud - Actualités cloud\n"
        "/tech - Actualités générales"
    )

def get_news(update, context, keyword):
    params = {
        "apiKey": NEWS_API_TOKEN,
        "q": keyword,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 3
    }
    try:
        response = requests.get(NEWSAPI_URL, params=params)
        data = response.json()
        articles = data.get("articles", [])

        if not articles:
            update.message.reply_text(f"Aucun article trouvé sur {keyword}.")
            return

        message = f"📰 Actus sur {keyword} :\n\n"
        for i, article in enumerate(articles, 1):
            title = article.get("title", "Sans titre")
            url = article.get("url", "#")
            source = article.get("source", {}).get("name", "Source inconnue")
            message += f"{i}. [{title}]({url})\n   Source: {source}\n\n"

        update.message.reply_text(message, parse_mode="Markdown", disable_web_page_preview=True)

    except Exception as e:
        update.message.reply_text(f"Erreur : {e}")

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help_command))
dispatcher.add_handler(CommandHandler("python", lambda u, c: get_news(u, c, "Python programming")))
dispatcher.add_handler(CommandHandler("js", lambda u, c: get_news(u, c, "JavaScript development")))
dispatcher.add_handler(CommandHandler("ai", lambda u, c: get_news(u, c, "Artificial Intelligence")))
dispatcher.add_handler(CommandHandler("cyber", lambda u, c: get_news(u, c, "Cybersecurity")))
dispatcher.add_handler(CommandHandler("react", lambda u, c: get_news(u, c, "React")))
dispatcher.add_handler(CommandHandler("cloud", lambda u, c: get_news(u, c, "Cloud computing")))
dispatcher.add_handler(CommandHandler("tech", lambda u, c: get_news(u, c, "Technology")))
dispatcher.add_handler(CommandHandler("search", search_news))

@app.route('/')
def index():
    return "✅ Bot is running."

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"

# === Webhook ===
if __name__ == '__main__':
    URL_RENDER = f"https://bot-veille-tech.onrender.com/{TELEGRAM_TOKEN}"
    bot.set_webhook(url=URL_RENDER)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
