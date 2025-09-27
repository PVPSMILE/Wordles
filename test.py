# main.py
import random
from telebot import TeleBot, types
from collections import Counter
from dotenv import load_dotenv
from collections import Counter
import os

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
bot = TeleBot(TOKEN)

# 🔧 NEW: імпортуємо наш модуль авторизації
import auth

# База загадок (парами: вопрос, ответ)
RIDDLES = [
    ("Что можно приготовить, но нельзя съесть?", "задание"),
    ("Он показывает время, но не говорит. Что это?", "часы"),
    ("Без окон, без дверей, а внутри живёт свет. Что это?", "лампочка"),
    ("У него есть экран, кнопки и голос, но он не человек. Что это?", "смартфон"),
    ("Летом зелёная, зимой дома стоит, украшенная. Что это?", "ёлка"),
    ("Весит можно скушать", "груша"),
]

user_state = {}  # chat_id -> {"answer": str, "question": str}
auth_flow = {}   # chat_id -> {"mode": "register"|"login", "step": int, ...}

def norm(s: str) -> str:
    """Нормализация для честного сравнения."""
    return (
        s.lower()
         .replace("ё", "е")
         .replace("—", "-")
         .replace(" ", "")
         .replace("-", "")
    )

@bot.message_handler(commands=['start'])
def on_start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Новая игра"))
    markup.add(types.KeyboardButton("Авторизация / Регистрация"))
    markup.add(types.KeyboardButton("Таблица лидеров"))
    
    bot.send_message(
        message.chat.id,
        "Привет! Это мини-игра «Слово-загадка».\n"
        "Я загадываю слово — ты вводишь ответ тем же словом.\n"
        "Команды: /new_game — начать новую игру.", reply_markup=markup 
    )
    new_game(message)
    
@bot.message_handler(func=lambda message: message.text == "Таблица лидеров")
def on_leaderboard(message): 
    leaderboard = "🏆 Таблица лидеров (тестовые данные):\n1. Игрок1 - 10 очков\n2. Игрок2 - 8 очков\n3. Игрок3 - 5 очков"
    bot.send_message(message.chat.id, leaderboard)

@bot.message_handler(func=lambda message: message.text == "Авторизация / Регистрация")
def on_reg_and_login(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Регистрация"))
    markup.add(types.KeyboardButton("Авторизация"))
    markup.add(types.KeyboardButton("⬅️ Назад в меню"))
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "⬅️ Назад в меню")
def back_to_menu(message):
    return on_start(message)

@bot.message_handler(func=lambda message: message.text == "Регистрация")
def on_reg(message): 
    chat_id = message.chat.id
    # 🔧 CHANGED: правильний режим — "register"
    auth_flow[chat_id] = {"mode": "register", "step": 1, "username": None, "password": None}
    bot.send_message(chat_id, "Давайте зарегистрируемся. Введите желаемый username:")

@bot.message_handler(func=lambda message: message.text == "Авторизация")
def on_login(message):
    chat_id = message.chat.id
    auth_flow[chat_id] = {"mode": "login", "step": 1, "username": None}
    bot.send_message(chat_id, "Введите ваш username:")

@bot.message_handler(func=lambda message: message.text == "Новая игра")
def on_new_game(message): 
    new_game(message)
    
@bot.message_handler(commands=['new_game'])
def new_game(message):
    chat_id = message.chat.id
    q, a = random.choice(RIDDLES)
    user_state[chat_id] = {"answer": a, "question": q}
    bot.send_message(chat_id, f"Отгадай загадку:\n\n{q}\n\n(введи слово ответом)")

# 🔧 NEW: універсальний обробник кроків auth_flow
@bot.message_handler(func=lambda m: m.chat.id in auth_flow and isinstance(m.text, str))
def handle_auth(m):
    chat_id = m.chat.id
    state = auth_flow.get(chat_id, {})
    mode = state.get("mode")

    if mode == "register":
        res = auth.register_flow_step(state, m.text, chat_id)
    elif mode == "login":
        res = auth.login_flow_step(state, m.text, chat_id)
    else:
        bot.send_message(chat_id, "Неизвестный режим. Попробуйте снова через меню.")
        auth_flow.pop(chat_id, None)
        return

    bot.send_message(chat_id, res["reply"])

    if res.get("done"):
        # завершили процес
        auth_flow.pop(chat_id, None)
        # за бажанням — показати кнопки
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("Новая игра"))
        markup.add(types.KeyboardButton("Таблица лидеров"))
        markup.add(types.KeyboardButton("⬅️ Назад в меню"))
        bot.send_message(chat_id, "Что дальше?", reply_markup=markup)
    else:
        # зберігаємо оновлений state (register_flow_step/login_flow_step змінюють його in-place)
        auth_flow[chat_id] = state


@bot.message_handler(func=lambda m: m.chat.id in user_state)
def handle_guess(message):
    chat_id = message.chat.id
    guess_raw = message.text.strip()
    answer_raw = user_state[chat_id]["answer"]

    guess = norm(guess_raw)
    answer = norm(answer_raw)

    if len(guess) != len(answer):
        bot.send_message(chat_id, f"В слове должно быть {len(answer)} букв(ы). Попробуй ещё.")
        return

    result = []
    correct_letters = set()
    misplaced_letters = set()
    wrong_letters = set()


    answer_counter = Counter(answer)

    for i, ch in enumerate(guess):
        if ch == answer[i]:
            result.append(ch)
            correct_letters.add(ch)
            answer_counter[ch] -= 1
        else:
            result.append("_")

    for i, ch in enumerate(guess):
        if result[i] == "_":
            if answer_counter.get(ch, 0) > 0:
                misplaced_letters.add(ch)
                answer_counter[ch] -= 1
            else:
                wrong_letters.add(ch)

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

bot.polling(none_stop=True)