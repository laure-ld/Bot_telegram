import psycopg2
import os

keywords = ["ai", "tech", "cyber"]

def connect_db():
    DATABASE_URL = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    return conn, cursor

def create_table_for_keyword(cursor, keyword):
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
    conn, cursor = connect_db()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT UNIQUE
        );
    """)
    for kw in keywords:
        create_table_for_keyword(cursor, kw)
    conn.commit()
    cursor.close()
    conn.close()

def sanitize_keyword(kw):
    kw = kw.lower().replace(" ", "_")
    if kw not in keywords:
        raise ValueError("Mot-clé non autorisé")
    return kw

def get_latest_articles(kw):
    conn, cursor = connect_db()
    try:
        table_name = sanitize_keyword(kw)
        cursor.execute(f"SELECT * FROM {table_name} ORDER BY date DESC LIMIT 5;")
        results = cursor.fetchall()
    except Exception as e:
        print(f"Erreur lors de la récupération des articles : {e}")
        results = []
    finally:
        cursor.close()
        conn.close()
    return results

def save_article_to_db(kw, title, url, date, summary):
    conn, cursor = connect_db()
    table_name = kw.lower().replace(" ", "_")
    cursor.execute(
        f"INSERT INTO {table_name} (title, url, date, summary) VALUES (%s, %s, %s, %s);",
        (title, url, date, summary))
    conn.commit()
    cursor.close()
    conn.close()

def delete_article(kw, article_id):
    conn, cursor = connect_db()
    try:
        table_name = sanitize_keyword(kw)
        cursor.execute(f"DELETE FROM {table_name} WHERE id = %s;", (article_id,))
        conn.commit()
    except Exception as e:
        print(f"Erreur lors de la suppression de l'article : {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    initialize_database()
    print("✅ Base de données initialisée.")
