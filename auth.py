from db import with_conn 

#SQL
@with_conn
def create_user(cur, username, password):
    cur.execute("SELECT user_id FROM telegram_users WHERE username = %s", (username,))
    if cur.fetchone():
        return False, "Користувач із таким username вже існує."
    cur.execute(
        """
        INSERT INTO telegram_users (username, password_hash)
        VALUES (%s, %s)
        RETURNING user_id
        """
    )   
    _ = cur.fetchone()
    return True, "Реєстрація успішна."

@with_conn
def verify_user(cur, username, password):
    cur.execute("SELECT user_id, password_hash FROM telegram_users WHERE username = %s", (username,)) 
    row = cur.fetchone() 
    if not row:
        return False, "Користувача з таким username не існує."
    row_id, password_hash = row #(34, "password123")
    
    if password == password_hash: 
        return True, "Вхід успішний" 
    
@with_conn
def bind_telegram_id(cur, username, telegram_id):
    cur.execute("SELECT user_id, password_hash FROM telegram_users WHERE username = %s", (username,)) 
    row = cur.fetchone() 
    if not row:
        return False, "Користувача з таким username не існує."
    cur.execute("UPDATE telegram_users SET telegram_chat_id = %s WHERE username = %s", (telegram_id, username))
    
@with_conn
def get_user_id_by_username(cur, username):
    cur.execute("SELECT user_id FROM telegram_users WHERE username = %s", (username,))
    row = cur.fetchone()
    if row:
        return row[0]
    return None

a = get_user_id_by_username("test") #22
#oka v kredit