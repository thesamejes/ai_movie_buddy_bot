
import logging
import requests
import openai
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# 🔐 ВСТАВЬ СЮДА СВОИ КЛЮЧИ
TELEGRAM_BOT_TOKEN = "8247478033:AAGktHw1rhHf9nUCk7lCj9nQFtV0eh5jkTo"
OPENROUTER_API_KEY = "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"
TMDB_API_KEY = "8f90cd15841e59f7856b8fd29af0829e"

openai.api_key = OPENROUTER_API_KEY
openai.api_base = "https://openrouter.ai/api/v1"

# 👉 Логирование
logging.basicConfig(level=logging.INFO)

# 🎬 Вопросы к пользователю
questions = [
    "Какое у тебя настроение сегодня? (например: грустно, спокойно, весело)",
    "Хочешь фильм или сериал?",
    "Смотришь один/одна или с кем-то?",
    "Предпочитаешь что-то новое или старое?",
    "На сколько времени у тебя есть (например: 1.5 часа, целый вечер)?"
]

user_answers = {}

# 🤖 Запрос к OpenRouter (GPT-подобная модель)
def ask_openrouter(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-3.5-turbo",  # ✅ Используем стабильную модель
        "messages": [
            {"role": "system", "content": "Ты — рекомендательный киноэксперт. Подбирай фильмы по настроению человека."},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        print("Status code:", response.status_code)
        print("Response:", response.text)

        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        print("❌ Ошибка при запросе к OpenRouter:", e)
        return "Ой, что-то пошло не так. Попробуй позже."

# 📽️ Поиск фильмов через TMDb
def search_movie(query):
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={query}"
    res = requests.get(url).json()
    if res['results']:
        movie = res['results'][0]
        return f"🎬 *{movie['title']}* ({movie.get('release_date', 'дата неизвестна')[:4]})\n" \
               f"⭐️ Рейтинг: {movie.get('vote_average', '?')}/10\n" \
               f"📄 {movie.get('overview', 'Нет описания')}\n" \
               f"https://www.themoviedb.org/movie/{movie['id']}"
    return "Фильм не найден 😢"

# 📲 Начало диалога
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_answers[update.effective_chat.id] = []
    await update.message.reply_text("Привет! 🎥 Я — AI Movie Buddy.\nДавай подберём тебе идеальный фильм или сериал.\n\n" + questions[0])
    return 0

# 🔄 Вопросы по очереди
async def handle_answers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    step = len(user_answers[chat_id])
    user_answers[chat_id].append(update.message.text)

    if step + 1 < len(questions):
        await update.message.reply_text(questions[step + 1])
        return step + 1
    else:
        await update.message.reply_text("Думаю над подборкой... 🍿")

        prompt = "Пользователь ответил:\n"
        for q, a in zip(questions, user_answers[chat_id]):
            prompt += f"{q} — {a}\n"
        prompt += "Подскажи 2-3 названия фильмов или сериалов, которые подойдут."

        try:
            gpt_reply = ask_openrouter(prompt)
            await update.message.reply_text("🤖 Вот что я подобрал:\n\n" + gpt_reply)

            # Поиск первого фильма в TMDb
            first_movie = gpt_reply.split("\n")[0].split("-")[0].strip("•1234567890. ").strip()
            if first_movie:
                info = search_movie(first_movie)
                await update.message.reply_markdown(info)
        except Exception as e:
            logging.error(f"Ошибка при генерации: {e}")
            await update.message.reply_text("Ой! Что-то пошло не так... Попробуй позже.")

        return ConversationHandler.END

# 🔚 Команда /cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог завершён. Напиши /start, чтобы начать заново.")
    return ConversationHandler.END

# ▶️ Основной запуск
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={i: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answers)] for i in range(len(questions))},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(conv_handler)

    print("Бот запущен ✅")
    app.run_polling()

if __name__ == "__main__":
    main()
