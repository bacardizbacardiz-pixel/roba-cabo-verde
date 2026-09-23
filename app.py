import os
import threading
from collections import defaultdict, deque

from flask import Flask
from openai import OpenAI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

client = OpenAI(api_key=OPENAI_API_KEY)

# Laikome paskutines grupės žinutes kontekstui.
# Vėliau galėsime pridėti nuolatinę atmintį.
history = defaultdict(lambda: deque(maxlen=100))

SYSTEM_PROMPT = """
Tu esi Roba – draugiškas AI asistentas privačioje Telegram grupėje
„Cabo Verde 2026“.

Kalbėk lietuviškai, nebent žmogus paprašo kitaip.
Grupė planuoja kelionę į Cabo Verde.
Atsakyk natūraliai, trumpai ir praktiškai.

Tau pateikiamas paskutinių grupės pokalbių kontekstas.
Naudok jį atsakydamas į klausimus, bet neišgalvok faktų,
kurių pokalbyje nėra.

Tu neturi atsakyti į kiekvieną grupės žinutę.
Atsakyk tik tada, kai žinutėje aiškiai kreipiamasi į Robą
arba paminimas tavo Telegram vartotojo vardas.
"""


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat = update.effective_chat
    user = update.effective_user
    text = update.message.text.strip()

    if not user or user.is_bot:
        return

    chat_id = chat.id
    name = user.first_name or user.username or "Dalyvis"

    # Išsaugome visas naujas grupės žinutes kaip kontekstą.
    history[chat_id].append(f"{name}: {text}")

    bot_username = (context.bot.username or "").lower()
    lower = text.lower()

    called_roba = (
        "roba" in lower
        or (bot_username and f"@{bot_username}" in lower)
    )

    if not called_roba:
        return

    conversation = "\n".join(history[chat_id])

    try:
        response = client.responses.create(
            model="gpt-5-mini",
            instructions=SYSTEM_PROMPT,
            input=(
                "Paskutinis grupės pokalbio kontekstas:\n\n"
                f"{conversation}\n\n"
                f"Naujausia žinutė, į kurią reikia atsakyti:\n{name}: {text}"
            ),
        )

        answer = response.output_text.strip()

        if answer:
            await update.message.reply_text(answer)

    except Exception as e:
        print(f"OpenAI error: {e}")
        await update.message.reply_text(
            "Roba dabar susidūrė su technine klaida 😅 Pabandyk dar kartą."
        )


def run_telegram():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    application.run_polling(drop_pending_updates=True)


# Render Web Service turi turėti HTTP serverį.
web = Flask(__name__)


@web.route("/")
def home():
    return "Roba Cabo Verde veikia 🦈"


if __name__ == "__main__":
    telegram_thread = threading.Thread(target=run_telegram, daemon=True)
    telegram_thread.start()

    port = int(os.environ.get("PORT", 10000))
    web.run(host="0.0.0.0", port=port)
