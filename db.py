# db.py
import os
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in .env")

# Проста пулінг-конфігурація
db_pool = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    dsn=DATABASE_URL
)

def get_conn():
    return db_pool.getconn()

def put_conn(conn):
    db_pool.putconn(conn)

def with_cursor(fn):
    """Декоратор для безпечної роботи з курсором і автокомітом."""
    def wrapper(*args, **kwargs):
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                res = fn(cur, *args, **kwargs)
                conn.commit()
                return res
        except Exception:
            conn.rollback()
            raise
        finally:
            put_conn(conn)
    return wrapper
