import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(os.environ["DATABASE_URL"])
cursor = conn.cursor()

keywords = ["ai", "tech", "cyber"]

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
    cursor.connection.commit()

def initialize_database():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT UNIQUE
        );
    """)
    for kw in keywords:
        create_table_for_keyword(kw)
    conn.commit()

def sanitize_keyword(kw):
    kw = kw.lower().replace(" ", "_")
    if kw not in keywords:
        raise ValueError("Mot-clé non autorisé")
    return kw

if __name__ == "__main__":
    initialize_database()

def get_latest_articles(kw):
    try:
        table_name = sanitize_keyword(kw)
        cursor.execute(f"SELECT * FROM {table_name} ORDER BY date DESC LIMIT 5;")
        return cursor.fetchall()
    except Exception as e:
        print(f"Erreur lors de la récupération des articles : {e}")
        return []

def save_article_to_db(kw, title, url, date, summary):
    table_name = kw.lower().replace(" ", "_")
    cursor.execute(
        f"INSERT INTO {table_name} (title, url, date, summary) VALUES (%s, %s, %s, %s);",
        (title, url, date, summary))
    cursor.connection.commit()

def delete_article(kw, article_id):
    try:
        table_name = sanitize_keyword(kw)
        cursor.execute(f"DELETE FROM {table_name} WHERE id = %s;", (article_id,))
        cursor.connection.commit()
    except Exception as e:
        print(f"Erreur lors de la suppression de l'article : {e}")

def close_db_connection():
    cursor.close()
    conn.close()