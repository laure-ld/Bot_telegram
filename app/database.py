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

def create_saved_articles_table():
    conn, cursor = connect_db()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS saved_articles (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT NOT NULL,
                keyword TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                summary TEXT,
                date TIMESTAMP
            );
        """)
        conn.commit()
        print("✅ Table 'saved_articles' créée (ou déjà existante).")
    except Exception as e:
        print(f"❌ Erreur lors de la création de la table : {e}")
    finally:
        cursor.close()
        conn.close()

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
        sanitized_kw = sanitize_keyword(kw)  # Nettoyage + sécurité
        cursor.execute(
            "DELETE FROM saved_articles WHERE keyword = %s AND id = %s;",
            (sanitized_kw, article_id)
        )
        if cursor.rowcount == 0:
            raise Exception("Aucun article trouvé avec cet ID dans cette catégorie.")
        conn.commit()
    except Exception as e:
        print(f"Erreur lors de la suppression de l'article : {e}")
        raise

if __name__ == "__main__":
    initialize_database()
    create_temporary_articles_table()
    create_saved_articles_table()
    print("✅ Base de données initialisée.")
