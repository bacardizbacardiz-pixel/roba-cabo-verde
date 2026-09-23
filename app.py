import os
import json
import threading
import urllib.request
from collections import defaultdict, deque

from flask import Flask, request, jsonify
from openai import OpenAI


# ============================================================
# NUSTATYMAI
# ============================================================

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

WEBHOOK_URL = "https://roba-cabo-verde.onrender.com/telegram"

client = OpenAI(api_key=OPENAI_API_KEY)

web = Flask(__name__)

# Laikina paskutinių 100 žinučių atmintis.
# Po Render restarto ji kol kas išsivalys.
history = defaultdict(lambda: deque(maxlen=100))


# ============================================================
# ROBOS CHARAKTERIS
# ============================================================

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
pvz. parašo „Roba“ arba pamini tavo Telegram vartotojo vardą.

Kai atsakai, elkis kaip normalus grupės dalyvis, o ne kaip
formalus klientų aptarnavimo botas.
"""


# ============================================================
# TELEGRAM API
# ============================================================

def telegram_api(method, payload=None):
    if payload is None:
        payload = {}

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/{method}"
    )

    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json"
        },
        method="POST"
    )

    with urllib.request.urlopen(
        req,
        timeout=30
    ) as response:

        result = json.loads(
            response.read().decode("utf-8")
        )

    if not result.get("ok"):
        raise RuntimeError(
            f"Telegram API klaida: {result}"
        )

    return result


# ============================================================
# ŽINUTĖS SIUNTIMAS
# ============================================================

def send_message(chat_id, text, reply_to_message_id=None):

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_to_message_id:
        payload["reply_parameters"] = {
            "message_id": reply_to_message_id
        }

    return telegram_api(
        "sendMessage",
        payload
    )


# ============================================================
# ROBOS ATSAKYMO GENERAVIMAS
# ============================================================

def process_message(
    chat_id,
    message_id,
    name,
    text
):
    try:
        print(
            f"Gauta Telegram zinute: {name}: {text}",
            flush=True
        )

        # Įsimename VISAS grupės tekstines žinutes.
        history[chat_id].append(
            f"{name}: {text}"
        )

        lower_text = text.lower()

        # Roba atsako tik tada, kai į jį kreipiamasi.
        called_roba = (
            "roba" in lower_text
            or "@robacaboverde_bot" in lower_text
        )

        if not called_roba:
            print(
                "Roba nepaminetas - zinute tik isiminta.",
                flush=True
            )
            return

        conversation = "\n".join(
            history[chat_id]
        )

        print(
            "Kreipiamasi i OpenAI...",
            flush=True
        )

        # Parodome Telegram "typing..."
        try:
            telegram_api(
                "sendChatAction",
                {
                    "chat_id": chat_id,
                    "action": "typing"
                }
            )
        except Exception as e:
            print(
                f"Typing klaida: {e}",
                flush=True
            )

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

        if not answer:
            print(
                "OpenAI grazino tuscia atsakyma.",
                flush=True
            )
            return

        send_message(
            chat_id,
            answer,
            message_id
        )

        print(
            "Roba atsake i Telegram.",
            flush=True
        )

    except Exception as e:

        print(
            f"ROBOS KLAIDA: {type(e).__name__}: {e}",
            flush=True
        )

        try:
            send_message(
                chat_id,
                "Roba dabar susidūrė su technine klaida 😅 "
                "Pabandyk dar kartą.",
                message_id
            )

        except Exception as send_error:

            print(
                f"Nepavyko issiusti klaidos zinutes: "
                f"{send_error}",
                flush=True
            )


# ============================================================
# PAGRINDINIS PUSLAPIS
# ============================================================

@web.route("/")
def home():
    return "Roba Cabo Verde veikia 🦈"


@web.route("/health")
def health():
    return "OK"


# ============================================================
# TELEGRAM WEBHOOK
# ============================================================

@web.route("/telegram", methods=["POST"])
def telegram_webhook():

    try:
        data = request.get_json(
            force=True,
            silent=False
        )

        print(
            f"Telegram webhook gautas. "
            f"Update ID: {data.get('update_id')}",
            flush=True
        )

        # Mus domina paprastos ir redaguotos žinutės.
        message = (
            data.get("message")
            or data.get("edited_message")
        )

        if not message:
            return "OK", 200

        text = message.get("text")

        if not text:
            return "OK", 200

        user = message.get("from", {})

        if user.get("is_bot"):
            return "OK", 200

        chat = message.get("chat", {})

        chat_id = chat.get("id")
        message_id = message.get("message_id")

        if not chat_id:
            return "OK", 200

        name = (
            user.get("first_name")
            or user.get("username")
            or "Dalyvis"
        )

        # SVARBIAUSIA:
        # Telegram iš karto gauna 200 OK.
        # OpenAI dirba atskirame threade.
        thread = threading.Thread(
            target=process_message,
            args=(
                chat_id,
                message_id,
                name,
                text.strip()
            ),
            daemon=True
        )

        thread.start()

        return "OK", 200

    except Exception as e:

        print(
            f"WEBHOOK KLAIDA: {type(e).__name__}: {e}",
            flush=True
        )

        # Telegram vis tiek duodame 200,
        # kad jis nekartotų tos pačios žinutės.
        return "OK", 200


# ============================================================
# WEBHOOK NUSTATYMAS
# ============================================================

@web.route("/setup-webhook")
def setup_webhook():

    try:
        result = telegram_api(
            "setWebhook",
            {
                "url": WEBHOOK_URL,
                "drop_pending_updates": True,
                "allowed_updates": [
                    "message",
                    "edited_message"
                ]
            }
        )

        print(
            f"Webhook nustatytas: {result}",
            flush=True
        )

        return jsonify({
            "status": "OK",
            "telegram": result
        })

    except Exception as e:

        print(
            f"Webhook setup klaida: {e}",
            flush=True
        )

        return jsonify({
            "status": "ERROR",
            "error": str(e)
        }), 500


# ============================================================
# WEBHOOK STATUSAS
# ============================================================

@web.route("/webhook-info")
def webhook_info():

    try:
        result = telegram_api(
            "getWebhookInfo"
        )

        return jsonify(result)

    except Exception as e:

        return jsonify({
            "status": "ERROR",
            "error": str(e)
        }), 500
