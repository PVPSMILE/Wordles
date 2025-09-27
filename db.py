import os
from dotenv import load_dotenv
import psycopg2
from psycopg2 import pool

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATBASE_URL erroris not find")

db_pool=pool.SimpleConnectionPool(
    minconn=1, maxconn=10, dsn=DATABASE_URL
)
def get_conn():
    return db_pool.getconn()
def put_conn(conn):
    db_pool.putconn(conn)
    
    
def with_conn(func):
    
    def wrapper(*args, **kwargs):
        conn = get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    res = func(cur, *args, **kwargs)
                    conn.commit()
                    return res
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            put_conn(conn)
    return wrapper