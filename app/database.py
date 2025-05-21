import psycopg2
import os

keywords = ["ai", "tech", "cyber", "archive"]

# Connexion à la base de données
def connect_db():
    DATABASE_URL = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    return conn, cursor

conn, cursor = connect_db()

# Création des tables
def create_table_for_keyword(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_articles (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT,
            keyword TEXT,
            title TEXT,
            url TEXT,
            summary TEXT,
            date TIMESTAMP
        );
    """)
    cursor.connection.commit()
create_table_for_keyword(cursor)

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

def create_temporary_articles_table():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS temporary_articles (
            article_id VARCHAR(10) PRIMARY KEY,
            chat_id BIGINT,
            keyword TEXT,
            title TEXT,
            url TEXT,
            summary TEXT,
            date TEXT
        );
    """)
    conn.commit()
create_temporary_articles_table()

# Nettoyage et validation d'un mot-clé fourni par l'utilisateur
def sanitize_keyword(kw):
    kw = kw.lower().replace(" ", "_")
    if kw not in keywords:
        raise ValueError("Mot-clé non autorisé")
    return kw

# Commande de base 
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

def delete_article(conn, cursor, kw, article_id):
    try:
        table_name = sanitize_keyword(kw)
        cursor.execute(f"DELETE FROM {table_name} WHERE id = %s;", (article_id,))
        conn.commit()
    except Exception as e:
        print(f"Erreur lors de la suppression de l'article : {e}")
        raise

if __name__ == "__main__":
    initialize_database()
    create_temporary_articles_table()
    print("✅ Base de données initialisée.")
