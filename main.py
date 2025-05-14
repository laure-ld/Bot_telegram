import os
import requests
import pytz
import psycopg2
import atexit
from datetime import datetime
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
NEWS_API_TOKEN = os.getenv("NEWS_API_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
NEWSAPI_URL = "https://newsapi.org/v2/everything"


# Connexion à PostgreSQL
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cursor = conn.cursor()

timezone = pytz.timezone('Europe/Paris')
scheduler = BackgroundScheduler(timezone=timezone)
bot = Bot(token=TELEGRAM_TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot=bot, update_queue=None, workers=4, use_context=True)

# Création des tables
def create_table_for_keyword(keyword):
    table_name = keyword.lower().replace(" ", "_")
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id SERIAL PRIMARY KEY,
            title TEXT,
            url TEXT,
            date TIMESTAMP,
            summary TEXT
        );
    """)
    conn.commit()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS subscribers (
        id SERIAL PRIMARY KEY,
        chat_id BIGINT UNIQUE
    );
""")
conn.commit()

# mots clés autorisé 
keywords = ["ai", "tech", "cyber"]

for kw in keywords:
    create_table_for_keyword(kw)

# === Commandes ===
def scheduler_daily():
    keywords = ["Technology", "Artificial Intelligence", "New technology"]
    cursor.execute("SELECT chat_id FROM subscribers;")
    subscribers = cursor.fetchall()

    intro_message = "👋 Hello ! J'espère que tu as bien dormi ! Voici les news du jour :"
    for (chat_id,) in subscribers:
        try:
            bot.send_message(chat_id=chat_id, text=intro_message)
        except Exception as e:
            print(f"Erreur d'envoi de l'intro à {chat_id} : {e}")

    for keyword in keywords:
        params = {
            "apiKey": NEWS_API_TOKEN,
            "q": keyword,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 2
        }
        try:
            response = requests.get(NEWSAPI_URL, params=params)
            data = response.json()
            articles = data.get("articles", [])

            if articles: 
                for article in articles:
                    title = article.get("title", "Sans titre")
                    url = article.get("url", "#")
                    date = article.get("publishedAt", "Date inconnue")
                    source = article.get("source", {}).get("name", "source inconnue")
                    summary = article.get("description", "Pas de résumé")
                    
                    article_message = (
                        f"📰 *{keyword}*\n"
                        f"*{title}*\n"
                        f"_{date}_ - {source}\n"
                        f"{summary}\n"
                        f"[Lire l'article]({url})"
                    )

                    for (chat_id,) in subscribers:
                        try:
                            bot.send_message(
                                chat_id=chat_id,
                                text=article_message,
                                parse_mode="Markdown",
                                disable_web_page_preview=True
                            )
                        except Exception as e:
                            print(f"❌ Erreur d'envoi à {chat_id} : {e}")                     
        except Exception as e:
                full_message += f"Erreur lors de la récupération des actualités {keyword}: {e}\n"
scheduler.add_job(scheduler_daily, 'cron', hour=9, minute=0)
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
            for article in articles:
                title = article.get("title", "Sans titre")
                url = article.get("url", "#")
                date = article.get("publishedAt", "Date inconnue")
                summary = article.get("description", "Pas de résumé")

                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"*{title}*\n_{date}_\n{summary}\n[Lire l'article]({url})",
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )
        else:
            update.message.reply_text(f"Erreur : {response.status_code}")
    except Exception as e:
        update.message.reply_text(f"Une erreur est survenue : {e}")

def start(update, context):
    chat_id = update.effective_chat.id
    cursor.execute("INSERT INTO subscribers (chat_id) VALUES (%s) ON CONFLICT DO NOTHING;", (chat_id,))
    conn.commit()
    update.message.reply_text("👋 Bienvenue dans le bot de veille techno ! Tape /help pour voir les commandes.")

def help_command(update, context):
    update.message.reply_text(
        "📚 Commandes disponibles :\n"
        "/ai - Actualités intelligence artificielle\n"
        "/cyber - Actualités cybersécurité\n"
        "/tech - Actualités générales\n"
        "/search <mot-clé> - la recheche que vous souhaitez\n"
        "/save <mot-clé> - Séléctionner l'artcle avant et sauvergarder\n"
        "/show <mot-clé> - Récuperer vos articles enregiistrer"
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
        for article in articles:
            title = article.get("title", "Sans titre")
            url = article.get("url", "#")
            date = article.get("publishedAt", "Date inconnue")
            summary = article.get("description", "Pas de résumé")

            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"*{title}*\n_{date}_\n{summary}\n[Lire l'article]({url})",
                parse_mode="Markdown",
                disable_web_page_preview=True
            )

    except Exception as e:
        update.message.reply_text(f"Erreur : {e}")

def save_article_to_db(kw, title, url, date, summary):
    table_name = kw.lower().replace(" ", "_")
    cursor.execute(
        f"INSERT INTO {table_name} (title, url, date, summary) VALUES (%s, %s, %s, %s);",
        (title, url, date, summary))
    conn.commit()

def get_latest_articles(kw):
    table_name = kw.lower().replace(" ", "_")
    cursor.execute(
        f"SELECT title, url, date, summary FROM {table_name} ORDER BY date  DESC LIMIT 5;"
    )
    rows = cursor.fetchall()
    return rows

def close_db_connection():
    cursor.close()
    conn.close()

def save_article (update, context):
    if len(context.args) < 1: 
        update.message.reply_text("Utilisation : /save <mot_clé>")
        return
    kw = context.args[0].lower().replace(" ", "_")

    if kw not in keywords:
        update.message.reply_text("Mot-clé non autorisé.")
        return
    
    title = "Article par default"
    url = "https://example.com"
    date = datetime.now()
    summary = "Résumé par défaut."

    cursor.execute(
        f"INSERT INTO {kw} (title, url, date, summary) VALUES (%s, %s, %s, %s);", (title, url, date, summary)
    )
    conn.commit()

    update.message.reply_text(f"Article ajouté avec succès dans la catégorie *{kw}*!")

def show_articles (update, context):
    if len(context.args) < 1 :
        update.message.reply_text("Utilisation : /show <mot_clé>")
        return
    kw = context.args[0].lower().replace(" ", "_")

    if kw not in keywords :
        update.message.reply_text("Mot-clé non reconnu.")
        return
    articles = get_latest_articles(kw)
    if not articles:
        update.message.reply_text("Aucun article trouvé.")
        return

    for article in articles :
        title, url, date, summary = article
        recup_message = (
            f"📰*{title}*\n"
            f"_{date}_\n"
            f"{summary}\n"
            f"[Lire l'article]({url})"
        )
        update.message.reply_text(text=recup_message, parse_mode="Markdown", disable_web_page_preview=True)

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help_command))
dispatcher.add_handler(CommandHandler("ai", lambda u, c: get_news(u, c, "Artificial Intelligence")))
dispatcher.add_handler(CommandHandler("cyber", lambda u, c: get_news(u, c, "Cybersecurity")))
dispatcher.add_handler(CommandHandler("tech", lambda u, c: get_news(u, c, "Technology")))
dispatcher.add_handler(CommandHandler("search", search_news))
dispatcher.add_handler(CommandHandler("save", save_article))
dispatcher.add_handler(CommandHandler("show", show_articles))

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
    URL_RENDER = f"https://veille-techno-bot.onrender.com/{TELEGRAM_TOKEN}"
    bot.set_webhook(url=URL_RENDER)
    atexit.register(close_db_connection)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
