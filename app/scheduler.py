from apscheduler.schedulers.background import BackgroundScheduler
from app.database import cursor
from app.config import NEWS_API_TOKEN, NEWS_API_URL
from app import bot
import requests
import pytz

scheduler = BackgroundScheduler()


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
    if error_log:
        print(error_log)
    pass
paris_tz = pytz.timezone('Europe/Paris')
scheduler = BackgroundScheduler(timezone=paris_tz)
scheduler.add_job(scheduler_daily, 'cron', hour=9, minute=0)
scheduler.start()