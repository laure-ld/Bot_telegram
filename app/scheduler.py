import requests
import pytz
import uuid
from apscheduler.schedulers.background import BackgroundScheduler
from app.database import cursor, temporary_articles
from app.config import NEWS_API_TOKEN, NEWS_API_URL
from app import bot
from app.database import conn
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Stockage temporaire des articles 
temp_articles = {}

# Gere l'interaction avec le button sauvergarder
def handle_callback(update, context):
    query = update.callback_query
    data = query.data

    if data.startswith("save|"):
        _, article_id = data.split("|")
        chat_id = query.message.chat.id

        # On récupère les infos de l'article temporaire
        cursor.execute(
            "SELECT keyword, title FROM temporary_articles WHERE article_id = %s AND chat_id = %s",
            (article_id, chat_id)
        )
        result = cursor.fetchone()

        if not result:
            query.answer("❌ Article introuvable.")
            return

        keyword, title = result

        try:
            cursor.execute(
                "INSERT INTO saved_articles (chat_id, keyword, title) VALUES (%s, %s, %s)",
                (chat_id, keyword, title)
            )
            conn.commit()
            query.answer("✅ Article sauvegardé !")
        except Exception as e:
            print(e)
            query.answer("❌ Erreur lors de la sauvegarde.")

# Fonction utilitaire : génère le message formaté pour un article
def format_article_message(keyword, title, date, source, summary, url):
    return (
        f"📰 *{keyword}*\n"
        f"*{title}*\n"
        f"_{date}_ - {source}\n"
        f"{summary}\n"
        f"[Lire l'article]({url})"
    )

paris_tz = pytz.timezone('Europe/Paris')
scheduler = BackgroundScheduler(timezone=paris_tz)

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

    error_log = ""

    for keyword in keywords:
        params = {
            "apiKey": NEWS_API_TOKEN,
            "q": keyword,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 2
        }

        try:
            response = requests.get(NEWS_API_URL, params=params)
            data = response.json()
            articles = data.get("articles", [])

            if articles:
                for article in articles:
                    title = article.get("title", "Sans titre")
                    url = article.get("url", "#")
                    date = article.get("publishedAt", "Date inconnue")
                    source = article.get("source", {}).get("name", "source inconnue")
                    summary = article.get("description", "Pas de résumé")

                    short_title = title[:30].replace('|', '')
                    short_summary = summary[:40].replace('|', '')
                    article_id = str(uuid.uuid4())[:8]

                    temp_articles[article_id] = {
                        "query": keyword,
                        "title": short_title,
                        "url": url,
                        "summary": short_summary,
                        "date": date
                    }

                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("💾 Sauvegarder", callback_data=f"save|{article_id}")]
                    ])

                    article_message = format_article_message(keyword, title, date, source, summary, url)

                    for (chat_id,) in subscribers:
                        # 🔽 Insertion correcte ici, après avoir toutes les données
                        try:
                            cursor.execute(
                                "INSERT INTO temporary_articles (article_id, chat_id, keyword, title, url, summary, date) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                                (article_id, chat_id, keyword, short_title, url, short_summary, date)
                            )
                            conn.commit()

                            bot.send_message(
                                chat_id=chat_id,
                                text=article_message,
                                parse_mode="Markdown",
                                reply_markup=keyboard,
                                disable_web_page_preview=True
                            )
                        except Exception as e:
                            print(f"❌ Erreur d'envoi ou d'insertion pour {chat_id} : {e}")
        except Exception as e:
            error_log += f"Erreur lors de la récupération des actualités '{keyword}' : {e}\n"

    if error_log:
        print(error_log)

scheduler.add_job(scheduler_daily, 'cron', hour=9, minute=0)
