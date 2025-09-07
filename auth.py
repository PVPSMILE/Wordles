# auth.py
from typing import Optional, Tuple
from passlib.hash import bcrypt
from db import with_cursor

@with_cursor
def create_user(cur, username: str, password: str) -> Tuple[bool, str]:
    """Повертає (ok, message). username унікальний."""
    cur.execute("SELECT user_id FROM telegram_users WHERE username = %s", (username,))
    if cur.fetchone():
        return False, "Користувач із таким username вже існує."

    pwd_hash = bcrypt.hash(password)
    cur.execute(
        """
        INSERT INTO telegram_users (username, password_hash)
        VALUES (%s, %s)
        RETURNING user_id
        """,
        (username, pwd_hash)
    )
    _ = cur.fetchone()
    return True, "Реєстрація успішна."

@with_cursor
def verify_user(cur, username: str, password: str) -> Tuple[bool, str]:
    cur.execute(
        "SELECT user_id, password_hash FROM telegram_users WHERE username = %s",
        (username,)
    )
    row = cur.fetchone()
    if not row:
        return False, "Невірний username або пароль."
    _, pwd_hash = row
    if not bcrypt.verify(password, pwd_hash):
        return False, "Невірний username або пароль."
    return True, "Успішний вхід."

@with_cursor
def bind_telegram(cur, username: str, chat_id: int) -> Tuple[bool, str]:
    """Привʼязує Telegram chat_id до користувача (опціонально)."""
    cur.execute("SELECT user_id FROM telegram_users WHERE username = %s", (username,))
    row = cur.fetchone()
    if not row:
        return False, "Користувача не знайдено."
    cur.execute(
        "UPDATE telegram_users SET telegram_chat_id = %s WHERE username = %s",
        (chat_id, username)
    )
    return True, "Telegram успішно привʼязано."

@with_cursor
def get_username_by_chat(cur, chat_id: int) -> Optional[str]:
    cur.execute(
        "SELECT username FROM telegram_users WHERE telegram_chat_id = %s",
        (chat_id,)
    )
    row = cur.fetchone()
    return row[0] if row else None




