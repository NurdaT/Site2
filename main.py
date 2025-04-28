from flask import Flask, render_template, request, jsonify, send_file
from gtts import gTTS
import requests
import os
import psycopg2
import psycopg2.extras

app = Flask(__name__)

# Настройки
MISTRAL_API_KEY = "CTWdz8rKGOHzxzVBsTjXHZkNh2D7kWhV"
AUDIO_OUTPUT = "static/response.mp3"

PROMPT = (
    "Ты — вежливый ассистент ресторана 'BurgerMaster'. "
    "Отвечай кратко. Используй информацию из меню бургеров."
)

DB_PARAMS = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'Burger',
    'user': 'postgres',
    'password': '124578'
}

# Подключение к БД
def get_db_connection():
    return psycopg2.connect(**DB_PARAMS)

# Получение бургеров
def get_burgers_data():
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT name, price, description FROM burger_burger;")
            return cur.fetchall()

# Генерация меню
def generate_menu_text():
    burgers = get_burgers_data()
    if not burgers:
        return "🍔 Меню пока пустое."

    menu = "🍔 Наше меню:\n"
    for i, b in enumerate(burgers, start=1):
        name = b['name']
        price = b['price']
        description = b['description'] or ""
        menu += f"{i}. {name} — {price}₸"
        if description:
            menu += f"\n   {description}"
        menu += "\n"
    return menu.strip()

# Обработка локальных запросов
def get_local_response(user_message):
    user_message = user_message.lower()
    burgers = get_burgers_data()

    if any(word in user_message for word in ["меню", "ассортимент", "что есть", "бургер"]):
        return generate_menu_text()

    for burger in burgers:
        if burger['name'].lower() in user_message:
            desc = burger['description'] or "вкусный бургер"
            return f"{burger['name']} — {desc}. Цена: {burger['price']}₸"

    if any(word in user_message for word in ["доставка", "привезти", "доставить"]):
        return "🚚 Доставка: 30-60 минут. Бесплатно от 5000₸, минимум — 2000₸."

    return None

# Mistral AI fallback
def get_mistral_response(user_message):
    local_response = get_local_response(user_message)
    if local_response:
        return local_response

    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mistral-medium",
        "messages": [
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.3,
        "max_tokens": 80
    }

    try:
        res = requests.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=data, timeout=5)
        return res.json()["choices"][0]["message"]["content"]
    except:
        return "Ошибка связи с AI. Попробуйте позже."

# Основной маршрут общения
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")
    mode = data.get("mode", "ai")

    if mode == "local":
        bot_response = get_local_response(user_message) or "Не нашёл такой информации в базе."
    else:
        bot_response = get_mistral_response(user_message)

    tts = gTTS(bot_response, lang="ru")
    tts.save(AUDIO_OUTPUT)

    return jsonify({
        "response": bot_response,
        "audio": AUDIO_OUTPUT
    })

@app.route("/audio")
def serve_audio():
    return send_file(AUDIO_OUTPUT, mimetype="audio/mpeg")

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    os.makedirs("static", exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=True)
