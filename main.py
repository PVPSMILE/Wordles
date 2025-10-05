import random
from telebot import TeleBot, types
from collections import Counter
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
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

user_state = {}  # chat_id -> {"answer": str, "question": str}
auth_flow = {} 

def norm(s: str) -> str:
    """Нормализация для честного сравнения."""
    return (
        s.lower()
         .replace("ё", "е")
         .replace("—", "-")
         .replace(" ", "")
         .replace("-", "")
    )

def main_menu_kb():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Новая игра"))
    markup.add(types.KeyboardButton("Авторизация / Регистрация"))
    markup.add(types.KeyboardButton("Таблица лидеров"))
    return markup

def auth_menu_kb():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Регистрация"))
    markup.add(types.KeyboardButton("Авторизация"))
    markup.add(types.KeyboardButton("⬅️ Назад в меню"))
    return markup
 
def cancel_kb():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("❌ Отмена"))
    return markup

def reset_game(chat_id):
    user_state.pop(chat_id, None)
    
def reset_auth(chat_id):
    auth_flow.pop(chat_id, None)

@bot.message_handler(commands=['start'])
def on_start(message):
    keyboard = main_menu_kb()
    
    bot.send_message(
        message.chat.id,
        "Привет! Это мини-игра «Слово-загадка».\n"
        "Я загадываю слово — ты вводишь ответ тем же словом.\n"
        "Команды: /new_game — начать новую игру.", reply_markup=keyboard 
    )
    new_game(message)

@bot.message_handler(func=lambda message: message.text == "Таблица лидеров")
def on_leaderboard(message): 
    leaderboard = "🏆 Таблица лидеров (тестовые данные):\n1. Игрок1 - 10 очков\n2. Игрок2 - 8 очков\n3. Игрок3 - 5 очков"
    bot.send_message(message.chat.id, leaderboard)

@bot.message_handler(func=lambda message: message.text == "Авторизация / Регистрация")
def on_reg_and_login(message):
    reset_auth(message.chat.id)
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=auth_menu_kb())

@bot.message_handler(func=lambda message: message.text == "Регистрация")
def on_reg(message): 
    chat_id = message.chat.id
    reset_game(chat_id)
    
    auth_flow[chat_id] = {"mode": "login", "step": 1, "username": None}
    bot.send_message(chat_id, "Введите ваш username:")
    

@bot.message_handler(func=lambda message: message.text == "Авторизация")
def on_login(message):
    chat_id = message.chat.id
    reset_game(chat_id)
    auth_flow[chat_id] = {"mode": "register", "step": 1, "username": None}
    bot.send_message(chat_id, "Введите ваш username:")
    

@bot.message_handler(func=lambda message: message.text == "Новая игра")
def on_new_game(message): 
    new_game(message)

@bot.message_handler(func=lambda message: message.text == "⬅️ Назад в меню")
def back_to_menu(message):
    markup = main_menu_kb()
    bot.send_message(message.chat.id, "Главное меню.", reply_markup=markup)

@bot.message_handler(commands=['new_game'])
def new_game(message):
    chat_id = message.chat.id
    q, a = random.choice(RIDDLES)
    user_state[chat_id] = {"answer": a, "question": q}
    bot.send_message(chat_id, f"Отгадай загадку:\n\n{q}\n\n(введи слово ответом)")

@bot.message_handler(func=lambda m: m.chat.id in user_state)
def handle_guess(message):
    chat_id = message.chat.id
    guess_raw = message.text.strip()
    answer_raw = user_state[chat_id]["answer"]

    guess = norm(guess_raw)
    answer = norm(answer_raw)

    # Проверка длины (после нормализации)
    if len(guess) != len(answer):
        bot.send_message(chat_id, f"В слове должно быть {len(answer)} букв(ы). Попробуй ещё.")
        return

    # Подсветка угаданных позиций + сбор статистики
    result = []
    correct_letters = set()
    misplaced_letters = set()
    wrong_letters = set()

    # Подсчёт частот для корректной «misplaced» логики
    answer_counter = Counter(answer)

    # Сначала отметим точные совпадения и вычтем их из частот
    for i, ch in enumerate(guess):
        if ch == answer[i]:
            result.append(ch)
            correct_letters.add(ch)
            answer_counter[ch] -= 1
        else:
            result.append("_")

    # Затем отметим «на месте/не на месте»
    for i, ch in enumerate(guess):
        if result[i] == "_":
            if answer_counter.get(ch, 0) > 0:
                misplaced_letters.add(ch)
                answer_counter[ch] -= 1
            else:
                wrong_letters.add(ch)

    # Проверка победы
    if "".join(result) == answer:
        bot.send_message(chat_id, f"🎉 Правильно! Это «{answer_raw}».")
        # Сброс и предложение новой игры
        user_state.pop(chat_id, None)
        bot.send_message(chat_id, "Хочешь ещё? Нажми /new_game")
        return

    # Формирование сообщения о прогрессе
    parts = [f"Результат: {' '.join(result)}"]
    if misplaced_letters:
        parts.append("Есть, но не на своих местах: " + ", ".join(sorted(misplaced_letters)))
    if wrong_letters:
        parts.append("Вообще нет в слове: " + ", ".join(sorted(wrong_letters)))

    bot.send_message(chat_id, "\n".join(parts))
    bot.send_message(chat_id, "Попробуй ещё раз!")

bot.polling(none_stop=True)