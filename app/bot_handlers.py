from telegram.ext import CommandHandler
from app import dispatcher
from datetime import datetime
from app.database import delete_article, get_latest_articles, conn, cursor, keywords
import requests
from app.config import NEWS_API_TOKEN, NEWS_API_URL

def save_article(update, context):
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

    pass

def show_articles(update, context):
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
        article_id, title, url, date, summary = article
        recup_message = (
            f"🆔 ID: {article_id}\n"
            f"📰*{title}*\n"
            f"_{date}_\n"
            f"{summary}\n"
            f"[Lire l'article]({url})"
        )
        update.message.reply_text(text=recup_message, parse_mode="Markdown", disable_web_page_preview=True)

    pass

def start(update, context):
    chat_id = update.effective_chat.id
    cursor.execute("INSERT INTO subscribers (chat_id) VALUES (%s) ON CONFLICT DO NOTHING;", (chat_id,))
    conn.commit()
    update.message.reply_text("👋 Bienvenue dans le bot de veille techno ! Tape /help pour voir les commandes.")
    pass

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
    pass

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
        response = requests.get(NEWS_API_URL, params=params)

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

def delete_article_command(update, context):
    if len(context.args) < 2 :
        update.message.reply_text("Utilisation : /delete <mot_clé> <id_article>")
        return
    kw = context.args[0].lower().replace(" ", "_")
    article_id = context.args[1]

    if kw not in keywords :
        update.message.reply_text("Mot-clé non reconnu.")
        return
    articles = get_latest_articles(kw)
    
    try:
        delete_article(cursor, kw, article_id)
        update.message.reply_text(f"🗑️ Article {article_id} supprimé avec succès de la catégorie {kw}.")
    except Exception as e:
        update.message.reply_text(f"❌ Erreur lors de la suppression : {e}")

def get_news(update, context, keyword):
    params = {
        "apiKey": NEWS_API_TOKEN,
        "q": keyword,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 3
    }
    try:
        response = requests.get(NEWS_API_URL, params=params)
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

# Ajouter les handlers au dispatcher
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help_command))
dispatcher.add_handler(CommandHandler("ai", lambda u, c: get_news(u, c, "Artificial Intelligence")))
dispatcher.add_handler(CommandHandler("cyber", lambda u, c: get_news(u, c, "Cybersecurity")))
dispatcher.add_handler(CommandHandler("tech", lambda u, c: get_news(u, c, "Technology")))
dispatcher.add_handler(CommandHandler("search", search_news))
dispatcher.add_handler(CommandHandler("save", save_article))
dispatcher.add_handler(CommandHandler("show", show_articles))
dispatcher.add_handler(CommandHandler("sup", delete_article_command))