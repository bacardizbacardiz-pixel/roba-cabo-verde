import os
import asyncio
import threading
from collections import defaultdict, deque

from flask import Flask, request
from openai import OpenAI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

# ==========================================
# NUSTATYMAI
# ==========================================

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

WEBHOOK_URL = "https://roba-cabo-verde.onrender.com/telegram"

client = OpenAI(api_key=OPENAI_API_KEY)

history = defaultdict(lambda: deque(maxlen=100))


# ==========================================
# ROBOS CHARAKTERIS
# ==========================================

SYSTEM_PROMPT = """
Tu esi Roba – draugiškas AI asistentas privačioje Telegram grupėje
„Cabo Verde 2026 🦈“.

Grupė planuoja kelionę į Cabo Verde.

Kalbėk lietuviškai, nebent žmogus aiškiai paprašo kitaip.
Bendrauk natūraliai, draugiškai ir neformaliai.
Atsakyk praktiškai ir ne per ilgai.

Tau pateikiamas paskutinių grupės pokalbių kontekstas.
Naudok jį, kad suprastum, apie ką grupės nariai kalba.

Neišgalvok faktų, kurių nežinai.

Tu matai visas naujas grupės tekstines žinutes, tačiau neturi
atsakyti į kiekvieną jų.

Atsakyk tik tada, kai žmogus aiškiai kreipiasi į Robą,
pvz. parašo „Roba“, arba pamini tavo Telegram vartotojo vardą.

Kai atsakai, elkis kaip normalus grupės dalyvis, o ne kaip
formalus klientų aptarnavimo botas.
"""


# ==========================================
# TELEGRAM ŽINUČIŲ APDOROJIMAS
# ==========================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.message or not update.message.text:
        return

    chat = update.effective_chat
    user = update.effective_user
    text = update.message.text.strip()

    if not chat or not user or user.is_bot:
        return

    chat_id = chat.id
    name = user.first_name or user.username or "Dalyvis"

    history[chat_id].append(f"{name}: {text}")

    lower_text = text.lower()
    bot_username = (context.bot.username or "").lower()

    called_roba = (
        "roba" in lower_text
        or (
            bot_username
            and f"@{bot_username}" in lower_text
        )
    )

    if not called_roba:
        return

    conversation = "\n".join(history[chat_id])

    try:
        response = client.responses.create(
            model="gpt-5.6-luna",
            instructions=SYSTEM_PROMPT,
            input=(
                "Paskutinis grupės pokalbio kontekstas:\n\n"
                f"{conversation}\n\n"
                "Dabar atsakyk į naujausią žinutę:\n"
                f"{name}: {text}"
            ),
        )

        answer = response.output_text.strip()

        if answer:
            await update.message.reply_text(answer)

    except Exception as e:
        print(f"OpenAI error: {e}", flush=True)

        await update.message.reply_text(
            "Roba dabar susidūrė su technine klaida 😅 "
            "Pabandyk dar kartą."
        )


# ==========================================
# TELEGRAM APPLICATION
# ==========================================

application = (
    ApplicationBuilder()
    .token(TELEGRAM_TOKEN)
    .updater(None)
    .build()
)

application.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    )
)

loop = asyncio.new_event_loop()


def run_telegram():
    asyncio.set_event_loop(loop)

    loop.run_until_complete(application.initialize())
    loop.run_until_complete(application.start())

    loop.run_forever()


telegram_thread = threading.Thread(
    target=run_telegram,
    daemon=True
)

telegram_thread.start()


# ==========================================
# RENDER / FLASK
# ==========================================

web = Flask(__name__)


@web.route("/")
def home():
    return "Roba Cabo Verde veikia 🦈"


@web.route("/health")
def health():
    return "OK"


@web.route("/telegram", methods=["POST"])
def telegram_webhook():
    data = request.get_json(force=True)

    update = Update.de_json(
        data,
        application.bot
    )

    asyncio.run_coroutine_threadsafe(
        application.update_queue.put(update),
        loop
    )

    return "OK", 200


# ==========================================
# WEBHOOK NUSTATYMAS
# ==========================================

async def setup_webhook():
    await application.bot.set_webhook(
        url=WEBHOOK_URL,
        drop_pending_updates=True
    )

    print(
        f"Telegram webhook nustatytas: {WEBHOOK_URL}",
        flush=True
    )


def configure_webhook():
    future = asyncio.run_coroutine_threadsafe(
        setup_webhook(),
        loop
    )

    try:
        future.result(timeout=30)
    except Exception as e:
        print(
            f"Webhook setup error: {e}",
            flush=True
        )


webhook_thread = threading.Thread(
    target=configure_webhook,
    daemon=True
)

webhook_thread.start()
