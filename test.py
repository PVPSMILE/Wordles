# main.py
import os
import random
from collections import Counter
from telebot import TeleBot, types
from dotenv import load_dotenv

from auth import create_user, verify_user, bind_telegram, get_username_by_chat

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN не задано в .env")

bot = TeleBot(TOKEN, parse_mode="HTML")

# ==== Твоя гра «слово-загадка» ====
RIDDLES = [
    ("Что можно приготовить, но нельзя съесть?", "задание"),
    ("Он показывает время, но не говорит. Что это?", "часы"),
    ("Без окон, без дверей, а внутри живёт свет. Что это?", "лампочка"),
    ("У него есть экран, кнопки и голос, но он не человек. Что это?", "смартфон"),
    ("Летом зелёная, зимой дома стоит, украшенная. Что это?", "ёлка"),
    ("Весит можно скушать", "груша"),
]

user_state = {}   # chat_id -> {"answer": str, "question": str}
auth_flow  = {}   # chat_id -> {"mode": "register"|"login", "step": 1|2, "username": str}

def norm(s: str) -> str:
    return (
        s.lower()
         .replace("ё", "е")
         .replace("—", "-")
         .replace(" ", "")
         .replace("-", "")
    )

# ==== Команди старт/меню ====
@bot.message_handler(commands=['start'])
def on_start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Быстрая игра")
    markup.add("Таблица лидеров")
    markup.add("Авторизация / Регистрация")

    bot.send_message(
        message.chat.id,
        "Привет! 👋 Это мини-игра «Слово-загадка».\n\n"
        "Выбери действие кнопкой ниже:",
        reply_markup=markup
    )

# --- Обработка кнопок ---
@bot.message_handler(func=lambda m: m.text == "Быстрая игра")
def on_quick_game(message):
    new_game(message)  # та же логика что и /new_game

@bot.message_handler(func=lambda m: m.text == "Таблица лидеров")
def on_leaderboard(message):
    # Пока тестовые данные
    leaderboard = "🏆 Таблица лидеров:\n1. Иван — 5 побед\n2. Мария — 3 победы\n3. Олег — 2 победы"
    bot.send_message(message.chat.id, leaderboard)

@bot.message_handler(func=lambda m: m.text == "Авторизация / Регистрация")
def on_auth_register(message):
    bot.send_message(
        message.chat.id,
        "Здесь будет логика авторизации и регистрации. 🚪\n"
        "Пока можешь считать, что эта кнопка работает 🙂"
    )


@bot.message_handler(commands=['new_game'])
def new_game_cmd(message):
    new_game(message)


def new_game(message):
    chat_id = message.chat.id
    q, a = random.choice(RIDDLES)
    user_state[chat_id] = {"answer": a, "question": q}
    bot.send_message(chat_id, f"Отгадай загадку:\n\n{q}\n\n(введи слово відповіддю)")

# ==== Реєстрація/логін як окремий діалог ====
@bot.message_handler(commands=['register'])
def register_cmd(message):
    chat_id = message.chat.id
    auth_flow[chat_id] = {"mode": "register", "step": 1}
    bot.send_message(chat_id, "Введи <b>username</b> для реєстрації:")

@bot.message_handler(commands=['login'])
def login_cmd(message):
    chat_id = message.chat.id
    auth_flow[chat_id] = {"mode": "login", "step": 1}
    bot.send_message(chat_id, "Введи <b>username</b> для входу:")

@bot.message_handler(func=lambda m: m.chat.id in auth_flow)
def handle_auth_flow(message):
    chat_id = message.chat.id
    flow = auth_flow[chat_id]
    mode = flow["mode"]
    step = flow["step"]

    # Крок 1: username
    if step == 1:
        flow["username"] = message.text.strip()
        flow["step"] = 2
        bot.send_message(chat_id, "Тепер введи <b>пароль</b>:")
        return

    # Крок 2: password -> виклик у auth.py
    if step == 2:
        password = message.text.strip()
        username = flow["username"]

        if mode == "register":
            ok, msg = create_user(username, password)
            if ok:
                # опціонально — привʼязка Telegram chat_id
                bind_telegram(username, chat_id)
            bot.send_message(chat_id, msg)
        elif mode == "login":
            ok, msg = verify_user(username, password)
            if ok:
                bind_telegram(username, chat_id)
            bot.send_message(chat_id, msg)

        auth_flow.pop(chat_id, None)
        return

# ==== Обробка відповідей у грі ====
@bot.message_handler(func=lambda m: m.chat.id in user_state)
def handle_guess(message):
    chat_id = message.chat.id
    guess_raw = message.text.strip()
    answer_raw = user_state[chat_id]["answer"]

    guess = norm(guess_raw)
    answer = norm(answer_raw)

    # Перевірка довжини
    if len(guess) != len(answer):
        bot.send_message(chat_id, f"У слові має бути {len(answer)} букв(и). Спробуй ще.")
        return

    result = []
    correct_letters = set()
    misplaced_letters = set()
    wrong_letters = set()

    from collections import Counter
    answer_counter = Counter(answer)

    # Точні збіги
    for i, ch in enumerate(guess):
        if ch == answer[i]:
            result.append(ch)
            correct_letters.add(ch)
            answer_counter[ch] -= 1
        else:
            result.append("_")

    # Літери «є, але не на місці»
    for i, ch in enumerate(guess):
        if result[i] == "_":
            if answer_counter.get(ch, 0) > 0:
                misplaced_letters.add(ch)
                answer_counter[ch] -= 1
            else:
                wrong_letters.add(ch)

    # Перемога
    if "".join(result) == answer:
        bot.send_message(chat_id, f"🎉 Правильно! Це «{answer_raw}».")
        user_state.pop(chat_id, None)
        bot.send_message(chat_id, "Ще раз? Натисни /new_game")
        return

    # Прогрес
    parts = [f"Результат: {' '.join(result)}"]
    if misplaced_letters:
        parts.append("Є, але не на своїх місцях: " + ", ".join(sorted(misplaced_letters)))
    if wrong_letters:
        parts.append("Взагалі немає в слові: " + ", ".join(sorted(wrong_letters)))

    bot.send_message(chat_id, "\n".join(parts))
    bot.send_message(chat_id, "Спробуй ще раз!")

if __name__ == "__main__":
    bot.polling(none_stop=True)
