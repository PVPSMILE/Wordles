# auth.py  (або aus.py)
# Дуже простий код реєстрації та входу для дітей.

from typing import Optional, Dict, Any
from db import with_cursor

# 1) Створюємо таблицю, якщо її ще немає
@with_cursor
def init_schema(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,   -- спрощено: без хешування
            chat_id BIGINT UNIQUE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            last_login TIMESTAMPTZ
        );
    """)

# 2) Допоміжні прості функції
@with_cursor
def get_user_by_username(cur, username: str) -> Optional[Dict[str, Any]]:
    cur.execute("SELECT id, username, password, chat_id FROM users WHERE username = %s", (username.strip().lower(),))
    row = cur.fetchone()
    if not row:
        return None
    return {"id": row[0], "username": row[1], "password": row[2], "chat_id": row[3]}

@with_cursor
def create_user(cur, username: str, password: str, chat_id: int):
    username = username.strip().lower()
    cur.execute("INSERT INTO users (username, password, chat_id) VALUES (%s, %s, %s) RETURNING id",
                (username, password, chat_id))
    return {"id": cur.fetchone()[0], "username": username}

@with_cursor
def link_chat_id(cur, user_id: int, chat_id: int):
    cur.execute("UPDATE users SET chat_id = %s WHERE id = %s", (chat_id, user_id))

@with_cursor
def update_last_login(cur, user_id: int):
    cur.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user_id,))

# 3) Прості «кроки» діалогу для реєстрації
#    Стан: {"mode":"register","step":1|2|3,"username":None,"password":None}
def register_flow_step(state: Dict[str, Any], text: str, chat_id: int) -> Dict[str, Any]:
    step = state.get("step", 1)

    # Крок 1: просимо username
    if step == 1:
        username = text.strip()
        if username == "":
            return {"reply": "Username не може бути порожнім. Введіть username:", "done": False, "ok": False, "user": None}
        if get_user_by_username(username):
            return {"reply": "Такий username вже існує. Введіть інший:", "done": False, "ok": False, "user": None}
        state["username"] = username
        state["step"] = 2
        return {"reply": "Введіть пароль:", "done": False, "ok": True, "user": None}

    # Крок 2: просимо пароль
    if step == 2:
        password = text.strip()
        if password == "":
            return {"reply": "Пароль не може бути порожнім. Введіть пароль:", "done": False, "ok": False, "user": None}
        state["password"] = password
        state["step"] = 3
        return {"reply": "Повторіть пароль ще раз:", "done": False, "ok": True, "user": None}

    # Крок 3: підтверджуємо пароль і створюємо користувача
    if step == 3:
        if text.strip() != state.get("password"):
            state["step"] = 2
            return {"reply": "Паролі не збігаються. Введіть пароль ще раз:", "done": False, "ok": False, "user": None}

        user = create_user(state["username"], state["password"], chat_id)
        return {
            "reply": f"✅ Реєстрація успішна! Ви увійшли як @{user['username']}.",
            "done": True,
            "ok": True,
            "user": user
        }

    # Якщо щось пішло не так — починаємо спочатку
    state["step"] = 1
    return {"reply": "Почнемо реєстрацію. Введіть бажаний username:", "done": False, "ok": True, "user": None}

# 4) Прості «кроки» діалогу для входу
#    Стан: {"mode":"login","step":1|2,"username":None}
def login_flow_step(state: Dict[str, Any], text: str, chat_id: int) -> Dict[str, Any]:
    step = state.get("step", 1)

    # Крок 1: питаємо username
    if step == 1:
        username = text.strip()
        user = get_user_by_username(username)
        if not user:
            return {"reply": "Користувача не знайдено. Спробуйте інший username:", "done": False, "ok": False, "user": None}
        state["username"] = user["username"]
        state["step"] = 2
        return {"reply": "Введіть пароль:", "done": False, "ok": True, "user": None}

    # Крок 2: перевіряємо пароль
    if step == 2:
        password = text.strip()
        user = get_user_by_username(state["username"])
        if not user or user["password"] != password:
            return {"reply": "Пароль невірний. Спробуйте ще раз:", "done": False, "ok": False, "user": None}

        # Прив’язуємо chat_id (якщо ще не прив’язаний)
        if not user.get("chat_id"):
            link_chat_id(user["id"], chat_id)
        update_last_login(user["id"])

        return {
            "reply": f"✅ Вхід успішний! Ви увійшли як @{user['username']}.",
            "done": True,
            "ok": True,
            "user": user
        }

    state["step"] = 1
    return {"reply": "Введіть ваш username:", "done": False, "ok": True, "user": None}

# 5) Ініціалізуємо таблицю одразу при імпорті
init_schema()
