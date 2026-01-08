import os
import sqlite3
from contextlib import contextmanager
from typing import List, Optional

from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

from openai import OpenAI

# ===================== ENV =====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

DB_PATH = os.getenv("DB_PATH", "my_database.db")

if not OPENAI_API_KEY:
    print("WARNING: OPENAI_API_KEY not set at startup")

if not os.path.exists(DB_PATH):
    print("WARNING: Database file not found. Running in cloud/demo mode.")

def get_openai_client():
    if not OPENAI_API_KEY:
        raise RuntimeError("OpenAI API key not configured.")
    return OpenAI(api_key=OPENAI_API_KEY)


# ===================== FASTAPI =====================
app = FastAPI(title="Olist Multi-Agent AI Backend (FINAL)")


@app.get("/")
def root():
    return {"status": "ok", "message": "Backend running (FINAL)"}


# ===================== DB UTILS =====================
@contextmanager
def get_connection():
    if not os.path.exists(DB_PATH):
        raise RuntimeError("Database not available in this environment.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def fetch_all(query: str, params: tuple = ()):
    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        print(f"DB QUERY FAILED: {e}")
        return []


def fetch_one(query: str, params: tuple = ()):
    rows = fetch_all(query, params)
    return rows[0] if rows else None


# ===================== HELPERS =====================
def normalize_category(cat: str) -> str:
    return cat.strip().lower().replace(" ", "_")


def get_category_translation_map():
    rows = fetch_all(
        "SELECT product_category_name, product_category_name_english FROM category_translation"
    )
    return {
        normalize_category(r["product_category_name_english"]): r["product_category_name"]
        for r in rows
    }


# ===================== AGENTS =====================
class SQLAgent:
    def average_price_by_category(self, category: str) -> Optional[float]:
        sql = """
        SELECT AVG(i.price) AS avg_price
        FROM items i
        JOIN products p ON i.product_id = p.product_id
        WHERE p.product_category_name = ?
          AND i.price IS NOT NULL
        """
        row = fetch_one(sql, (category,))
        return row["avg_price"] if row and row["avg_price"] else None

    def list_categories(self) -> List[str]:
        rows = fetch_all(
            "SELECT DISTINCT product_category_name FROM products WHERE product_category_name IS NOT NULL"
        )
        categories = sorted({r["product_category_name"] for r in rows})

        # Fallback jika DB tidak tersedia / kosong
        if not categories:
            return [
                "furniture",
                "electronics",
                "auto",
                "toys",
                "fashion",
                "sports",
                "home_appliances",
                "books",
                "health_beauty",
            ]

        return categories



    def seller_performance(self, city: str):
        sql = """
        SELECT s.seller_city,
               COUNT(o.order_id) AS total_orders,
               AVG(r.review_score) AS avg_review
        FROM sellers s
        JOIN items i ON s.seller_id = i.seller_id
        JOIN orders o ON i.order_id = o.order_id
        LEFT JOIN reviews r ON o.order_id = r.order_id
        WHERE LOWER(s.seller_city) = LOWER(?)
        GROUP BY s.seller_city
        """
        return fetch_one(sql, (city,))


class RAGAgent:
    def most_positive_reviewed_product(self):
        sql = """
        SELECT p.product_id,
               COUNT(r.review_score) AS review_count,
               AVG(r.review_score) AS avg_score
        FROM products p
        JOIN items i ON p.product_id = i.product_id
        JOIN reviews r ON i.order_id = r.order_id
        WHERE r.review_score >= 4
        GROUP BY p.product_id
        ORDER BY review_count DESC
        LIMIT 1
        """
        return fetch_one(sql)


class RecommendationAgent:
    def best_products(self, limit: int = 5):
        sql = """
        SELECT p.product_id,
               COUNT(r.review_score) AS total_reviews,
               AVG(r.review_score) AS avg_score
        FROM products p
        JOIN items i ON p.product_id = i.product_id
        JOIN reviews r ON i.order_id = r.order_id
        GROUP BY p.product_id
        HAVING avg_score >= 4
        ORDER BY avg_score DESC, total_reviews DESC
        LIMIT ?
        """
        return fetch_all(sql, (limit,))


# ===================== ORCHESTRATOR =====================
class Orchestrator:
    def __init__(self):
        self.sql = SQLAgent()
        self.rag = RAGAgent()
        self.rec = RecommendationAgent()

    def run(self, question: str) -> str:
        q = question.lower()

        # === KATEGORI ===
        if "kategori apa" in q:
            cats = self.sql.list_categories()
            if not cats:
                return "Kategori tersedia namun data detail tidak dimuat pada environment cloud."

            return "Kategori yang tersedia:\n- " + "\n- ".join(cats)


        # === AVERAGE PRICE ===
        if "harga rata rata" in q or "rata-rata harga" in q:
            trans = get_category_translation_map()
            for k_en, k_id in trans.items():
                if k_en in q:
                    avg = self.sql.average_price_by_category(k_id)
                    if avg is None:
                        return f"Tidak ditemukan harga valid untuk kategori {k_en}."
                    return f"Rata-rata harga produk kategori {k_en} adalah {avg:.2f}."

        # === SELLER PERFORMANCE ===
        if "performa seller" in q or "bandingkan seller" in q:
            if "sao paulo" in q or "são paulo" in q:
                res = self.sql.seller_performance("sao paulo")
                return f"Seller São Paulo: {res}" if res else "Data São Paulo tidak ditemukan."
            if "rio" in q:
                res = self.sql.seller_performance("rio de janeiro")
                return f"Seller Rio de Janeiro: {res}" if res else "Data Rio tidak ditemukan."

        # === RAG ===
        if "paling sering direview positif" in q:
            res = self.rag.most_positive_reviewed_product()
            if not res:
                return "Tidak ditemukan produk dengan review positif."
            return (
                f"Produk dengan review positif terbanyak adalah "
                f"{res['product_id']} dengan {res['review_count']} review positif."
            )

        # === RECOMMENDATION ===
        if "produk terbaik" in q or "produk paling bagus" in q:
            recs = self.rec.best_products()
            if not recs:
                return "Belum cukup data untuk rekomendasi produk."
            lines = [
                f"{r['product_id']} (rating {r['avg_score']:.2f}, {r['total_reviews']} review)"
                for r in recs
            ]
            return "Rekomendasi produk terbaik:\n- " + "\n- ".join(lines)

        return "Pertanyaan belum didukung oleh sistem."


# ===================== API SCHEMA =====================
class ChatRequest(BaseModel):
    query: str


class ChatResponse(BaseModel):
    answer: str


agent = Orchestrator()


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    answer = agent.run(req.query)
    return ChatResponse(answer=answer)
