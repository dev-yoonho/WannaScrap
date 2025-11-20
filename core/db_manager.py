import sqlite3
import os

from datetime import datetime

DB_PATH = os.path.join("news_data", "articles.db")

def init_db():
    os.makedirs("news_data", exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
                    CREATE TABLE IF NOT EXISTS articles (
                                                            index_number INTEGER PRIMARY KEY,
                                                            title TEXT NOT NULL,
                                                            link TEXT NOT NULL,
                                                            pub_date TEXT,
                                                            source TEXT,
                                                            body TEXT,
                                                            saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """)
        conn.commit()


def save_article(article):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        # saved_at을 직접 넣는다
        cur.execute("""
            INSERT OR REPLACE INTO articles (
                index_number, title, link, pub_date, source, body, saved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            article["id"],
            article["title"],
            article["link"],
            article["pub_date"],
            article["source"],
            article["body"],
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 저장일 명시적으로 입력
        ))
        conn.commit()

def load_article(index_number):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT source, body FROM articles WHERE index_number = ?", (index_number,))
        return cur.fetchone()

def load_all_articles():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT index_number, title, link, pub_date, source, body, saved_at FROM articles")
        return cur.fetchall()

def delete_article(index_number):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM articles WHERE index_number = ?", (index_number,))
        conn.commit()
