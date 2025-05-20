import requests
import uuid
from telegram.ext import CommandHandler
from app import dispatcher
from app.database import delete_article, get_latest_articles, sanitize_keyword, conn, cursor, keywords
from app.config import NEWS_API_TOKEN, NEWS_API_URL
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

# Gere l'interaction avec le button sauvergarder
def handle_callback(update, context):
    query = update.callback_query
    data = query.data

    query.answer()

    if data.startswith("save|"):
        _, article_id = data.split("|")
        chat_id = query.message.chat.id

        try:
            cursor.execute(
                "SELECT keyword, title, url, summary, date FROM temporary_articles WHERE article_id = %s AND chat_id = %s",
                (article_id, chat_id)
            )
            result = cursor.fetchone()

            if not result:
                query.answer("❌ Article introuvable.")
                return

            keyword, title, url, summary, date = result

            cursor.execute(
                "SELECT 1 FROM saved_articles WHERE chat_id = %s AND title = %s",
                (chat_id, title)
            )
            if cursor.fetchone():
                query.answer("⚠️ Article déjà sauvegardé.")
                return

            cursor.execute(
                "INSERT INTO saved_articles (chat_id, keyword, title, url, summary, date) VALUES (%s, %s, %s, %s, %s, %s);",
                (chat_id, keyword, title, url, summary, date)
            )
            conn.commit()
            query.answer("✅ Article sauvegardé !")

        except Exception as e:
            print(f"Erreur lors de la sauvegarde : {e}")
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

# Commande principale 
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
        "/show <mot-clé> - Récuperer vos articles enregistrés"
    )

def show_articles(update, context):
    if len(context.args) < 1:
        update.message.reply_text("Utilisation : /show <mot_clé>")
        return

    keyword = context.args[0].lower().replace(" ", "_")

    if keyword not in keywords:
        update.message.reply_text("Mot-clé non reconnu.")
        return

    chat_id = update.effective_chat.id

    try:
        cursor.execute(
            "SELECT id, title, url, date, summary FROM saved_articles WHERE chat_id = %s AND keyword = %s ORDER BY date DESC",
            (chat_id, keyword)
        )
        articles = cursor.fetchall()

        if not articles:
            update.message.reply_text("Aucun article sauvegardé pour ce mot-clé.")
            return

        for article in articles:
            article_id, title, url, date, summary = article
            recup_message = (
                f"🆔 ID: {article_id}\n"
                f"📰 *{title}*\n"
                f"📅 _{date}_\n"
                f"{summary}\n"
                f"[Lire l'article]({url})"
            )
            update.message.reply_text(
                text=recup_message,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
    except Exception as e:
        update.message.reply_text(f"❌ Erreur lors de la récupération : {e}")

def search_news(update, context):
    if not context.args:
        update.message.reply_text("Utilisation : /search <mot-clé>")
        return

    query = " ".join(context.args)
    keyword = query.lower().replace(" ", "_")

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

            chat_id = update.effective_chat.id

            for article in articles:
                title = article.get("title", "Sans titre")
                url = article.get("url", "#")
                date = article.get("publishedAt", "Date inconnue")
                source = article.get("source", {}).get("name", "source inconnue")
                summary = article.get("description", "Pas de résumé")

                short_title = (title or "")[:30].replace('|', '')
                short_summary = (summary or "")[:40].replace('|', '')
                article_id = str(uuid.uuid4())[:8]

                cursor.execute(
                    "INSERT INTO temporary_articles (article_id, chat_id, keyword, title, url, summary, date) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (article_id, chat_id, keyword, short_title, url, short_summary, date)
                )

                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("💾 Sauvegarder", callback_data=f"save|{article_id}")]
                ])
                message = format_article_message(query, title, date, source, summary, url)

                context.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                    disable_web_page_preview=True
                )
            conn.commit()

        else:
            update.message.reply_text(f"Erreur API : {response.status_code}")
    except Exception as e:
        update.message.reply_text(f"❌ Une erreur est survenue : {e}")

def delete_article_command(update, context):
    if len(context.args) < 2 :
        update.message.reply_text("Utilisation : /delete <mot_clé> <id_article>")
        return
    kw = context.args[0].lower().replace(" ", "_")
    article_id = context.args[1]

    if kw not in keywords :
        update.message.reply_text("Mot-clé non reconnu.")
        return
    
    try:
        delete_article(cursor, kw, article_id)
        update.message.reply_text(f"🗑️ Article {article_id} supprimé avec succès de la catégorie {kw}.")
    except Exception as e:
        update.message.reply_text(f"❌ Erreur lors de la suppression : {e}")

def search_keyword_news(update, context, fixed_keyword=None):
    try:
        if fixed_keyword:
            keyword = sanitize_keyword(fixed_keyword)
        else:
            keyword = sanitize_keyword(" ".join(context.args))
    except ValueError:
        update.message.reply_text("❌ Mot-clé non autorisé.")
        return

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

        for article in articles:
            title = article.get("title", "Sans titre")
            url = article.get("url", "#")
            date = article.get("publishedAt", "Date inconnue")
            summary = article.get("description", "Pas de résumé")

            short_title = title[:30].replace('|', '')
            short_summary = summary[:40].replace('|', '')
            article_id = str(uuid.uuid4())[:8]
            chat_id = update.effective_chat.id

            try:
                cursor.execute(
                    "INSERT INTO temporary_articles (article_id, chat_id, keyword, title, url, summary, date) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (article_id, chat_id, keyword, short_title, url, short_summary, date)
                )
                conn.commit()
            except Exception as e:
                print(f"Erreur DB : {e}")

            article_message = format_article_message(keyword, title, date, article.get("source", {}).get("name", "Source inconnue"), summary, url)

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💾 Sauvegarder", callback_data=f"save|{article_id}")]
            ])

            try:
                context.bot.send_message(
                    chat_id=chat_id,
                    text=article_message,
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                    disable_web_page_preview=True
                )
            except Exception as e:
                update.message.reply_text(f"❌ Erreur d'envoi d'article : {e}")

    except Exception as e:
        update.message.reply_text(f"❌ Erreur : {e}")

# Ajouter les handlers au dispatcher
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help_command))
dispatcher.add_handler(CommandHandler("ai", lambda u, c: search_keyword_news(u, c, "ai")))
dispatcher.add_handler(CommandHandler("cyber", lambda u, c: search_keyword_news(u, c, "cyber")))
dispatcher.add_handler(CommandHandler("tech", lambda u, c: search_keyword_news(u, c, "tech")))
dispatcher.add_handler(CommandHandler("search", search_news))
dispatcher.add_handler(CommandHandler("show", show_articles))
dispatcher.add_handler(CommandHandler("sup", delete_article_command))
dispatcher.add_handler(CallbackQueryHandler(handle_callback))
