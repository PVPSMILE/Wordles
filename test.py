# main.py
import os
import random
from collections import Counter
from dotenv import load_dotenv
from telebot import TeleBot, types

# Прості auth-функції (без хешування)
from auth import create_user, verify_user, bind_telegram_id

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в .env")

bot = TeleBot(TOKEN)

# База загадок (парами: вопрос, ответ)
RIDDLES = [
    ("Что можно приготовить, но нельзя съесть?", "задание"),
    ("Он показывает время, но не говорит. Что это?", "часы"),
    ("Без окон, без дверей, а внутри живёт свет. Что это?", "лампочка"),
    ("У него есть экран, кнопки и голос, но он не человек. Что это?", "смартфон"),
    ("Летом зелёная, зимой дома стоит, украшенная. Что это?", "ёлка"),
    ("Весит можно скушать", "груша"),
    ("Что можно видеть закрытыми глазами ", "сон"),
    ("Белые сережки на зеленой ножке", "ландыши"),
    ("Без рук, без ног, а рисует", "молния"),
    ("Сто одежек и все без застежек", "капуста"),
    ("Зимой и летом одним цветом", "ёлка"),
    ("Не лает, не кусает, в дом не пускает", "замок"),
    ("Сидит дед во сто шуб одет", "капуста"),
    ("Висит груша нельзя скушать", "лампочка"),
    ("Не птица, а летает, не зверь, а рычит", "самолет"),
    ("Летит - молчит, стоит - говорит", "фонарь"),
    ("Кто на себе носит дом?", "улитка"),
    ("Что можно приготовить, но нельзя съесть?", "задание"),
    ("Что принадлежит вам, но другие используют его чаще, чем вы?", "имя"),
    ("Что можно сломать, не касаясь его?", "обещание"),
    ("Что всегда перед вами, но не может быть увидено?", "будущее"),
    ("Что можно поймать, но нельзя бросить?", "простуда"),
    
]

# Состояния
user_state = {}   # chat_id -> {"answer": str, "question": str}
auth_flow = {}    # chat_id -> {"mode": "register"|"login", "step": 1|2, "username": str|None}

# ==== helpers ====
def norm(s: str) -> str:
    return (s or "").lower().replace("ё", "е").replace("—", "-").replace(" ", "").replace("-", "")

def main_menu_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("Новая игра"))
    kb.add(types.KeyboardButton("Авторизация / Регистрация"))
    kb.add(types.KeyboardButton("Таблица лидеров"))
    return kb

def auth_menu_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("Регистрация"))
    kb.add(types.KeyboardButton("Авторизация"))
    kb.add(types.KeyboardButton("⬅️ Назад в меню"))
    return kb

def cancel_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("❌ Отмена"))
    return kb

def reset_auth(chat_id): auth_flow.pop(chat_id, None)
def reset_game(chat_id): user_state.pop(chat_id, None)

# ==== команды ====
@bot.message_handler(commands=['start'])
def on_start(message):
    bot.send_message(
        message.chat.id,
        "Привет! Это мини-игра «Слово-загадка».\n"
        "Команды: /new_game — новая игра, /cancel — отмена действия.",
        reply_markup=main_menu_kb()
    )

@bot.message_handler(commands=['new_game'])
def new_game(message):
    chat_id = message.chat.id
    q, a = random.choice(RIDDLES)
    user_state[chat_id] = {"answer": a, "question": q}
    bot.send_message(chat_id, f"Отгадай загадку:\n\n{q}\n\n(введи слово ответом)")

@bot.message_handler(commands=['cancel'])
def cmd_cancel(message):
    reset_auth(message.chat.id)
    bot.send_message(message.chat.id, "Ок, отменил текущее действие.", reply_markup=main_menu_kb())

# ==== главное меню ====
@bot.message_handler(func=lambda m: m.text == "Новая игра")
def on_new_game(message): 
    new_game(message)

@bot.message_handler(func=lambda m: m.text == "Таблица лидеров")
def on_leaderboard(message): 
    leaderboard = "🏆 Таблица лидеров (тест):\n1. Игрок1 - 10\n2. Игрок2 - 8\n3. Игрок3 - 5"
    bot.send_message(message.chat.id, leaderboard)

@bot.message_handler(func=lambda m: m.text == "Авторизация / Регистрация")
def on_reg_and_login(message):
    reset_auth(message.chat.id)
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=auth_menu_kb())

@bot.message_handler(func=lambda m: m.text == "⬅️ Назад в меню")
def back_to_menu(message):
    reset_auth(message.chat.id)
    bot.send_message(message.chat.id, "Главное меню.", reply_markup=main_menu_kb())

# ==== флоу Регистрация / Авторизация ====
@bot.message_handler(func=lambda m: m.text == "Регистрация")
def reg_start(message):
    chat_id = message.chat.id
    reset_game(chat_id)  # чтобы игра не перехватывала ввод
    auth_flow[chat_id] = {"mode": "register", "step": 1, "username": None}
    bot.send_message(chat_id, "Введите ваш username:", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: m.text == "Авторизация")
def login_start(message):
    chat_id = message.chat.id
    reset_game(chat_id)  # чтобы игра не перехватывала ввод
    auth_flow[chat_id] = {"mode": "login", "step": 1, "username": None}
    bot.send_message(chat_id, "Введите ваш username:", reply_markup=cancel_kb())

@bot.message_handler(func=lambda m: m.text == "❌ Отмена")
def on_cancel_btn(message):
    cmd_cancel(message)

@bot.message_handler(func=lambda m: m.chat.id in auth_flow)
def handle_auth(message):
    chat_id = message.chat.id
    st = auth_flow.get(chat_id, {})
    mode = st.get("mode")
    step = st.get("step", 0)
    text = (message.text or "").strip()

    # Регистрация: username -> password
    if mode == "register":
        if step == 1:
            st["username"], st["step"] = text, 2
            bot.send_message(chat_id, "Введите пароль:")
            return
        if step == 2:
            try:
                ok, msg = create_user(st["username"], text)
            except Exception as e:
                ok, msg = False, f"Ошибка БД: {e}"
            if not ok:
                st["step"] = 1
                bot.send_message(chat_id, f"Не удалось зарегистрировать: {msg}\nВведите другой username:")
                return
            # Привязка chat_id (не критично, поэтому без жёсткой обработки ошибок)
            try:
                bind_telegram_id(st["username"], chat_id)
            except Exception:
                pass
            reset_auth(chat_id)
            bot.send_message(chat_id, "✅ Регистрация успешна!", reply_markup=main_menu_kb())
            return

    # Авторизация: username -> password
    if mode == "login":
        if step == 1:
            st["username"], st["step"] = text, 2
            bot.send_message(chat_id, "Введите пароль:")
            return
        if step == 2:
            try:
                ok, msg = verify_user(st["username"], text)
            except Exception as e:
                ok, msg = False, f"Ошибка БД: {e}"
            if not ok:
                st["step"] = 1
                bot.send_message(chat_id, f"Вход неуспешен: {msg}\nВведите username ещё раз:")
                return
            try:
                bind_telegram_id(st["username"], chat_id)
            except Exception:
                pass
            reset_auth(chat_id)
            bot.send_message(chat_id, "✅ Вход успешен!", reply_markup=main_menu_kb())
            return

# ==== игра ====
@bot.message_handler(func=lambda m: (m.chat.id in user_state) and (m.chat.id not in auth_flow))
def handle_guess(message):
    chat_id = message.chat.id
    guess_raw = (message.text or "").strip()
    answer_raw = user_state[chat_id]["answer"]

    guess = norm(guess_raw)
    answer = norm(answer_raw)

    # Проверка длины (после нормализации)
    if len(guess) != len(answer):
        bot.send_message(chat_id, f"В слове должно быть {len(answer)} букв(ы). Попробуй ещё.")
        return

    # Подсветка угаданных позиций + сбор статистики
    result = []
    misplaced_letters = set()
    wrong_letters = set()
    answer_counter = Counter(answer)

    # Точные совпадения
    for i, ch in enumerate(guess):
        if ch == answer[i]:
            result.append(ch)
            answer_counter[ch] -= 1
        else:
            result.append("_")

    # Есть в слове, но не на месте / нет в слове
    for i, ch in enumerate(guess):
        if result[i] == "_":
            if answer_counter.get(ch, 0) > 0:
                misplaced_letters.add(ch)
                answer_counter[ch] -= 1
            else:
                wrong_letters.add(ch)

    # Победа
    if "".join(result) == answer:
        bot.send_message(chat_id, f"🎉 Правильно! Это «{answer_raw}».")
        user_state.pop(chat_id, None)
        bot.send_message(chat_id, "Хочешь ещё? Нажми /new_game")
        return

    parts = [f"Результат: {' '.join(result)}"]
    if misplaced_letters:
        parts.append("Есть, но не на своих местах: " + ", ".join(sorted(misplaced_letters)))
    if wrong_letters:
        parts.append("Вообще нет в слове: " + ", ".join(sorted(wrong_letters)))

    bot.send_message(chat_id, "\n".join(parts))
    bot.send_message(chat_id, "Попробуй ещё раз!")

if __name__ == "__main__":
    bot.polling(none_stop=True, timeout=60)
