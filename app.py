import os
import json
import base64
import threading
import urllib.request
from collections import defaultdict, deque

from flask import Flask, request, jsonify
from openai import OpenAI


TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

WEBHOOK_URL = "https://roba-cabo-verde.onrender.com/telegram"

client = OpenAI(api_key=OPENAI_API_KEY)
web = Flask(__name__)

# Laikina grupės pokalbio atmintis.
# Po Render restarto ji išsivalys.
history = defaultdict(lambda: deque(maxlen=100))


SYSTEM_PROMPT = """
Tu esi Roba – draugiškas AI asistentas privačioje Telegram grupėje
„Cabo Verde 2026 🦈“.

Grupė planuoja kelionę į Cabo Verde.

Kalbėk lietuviškai, nebent žmogus aiškiai paprašo kitaip.
Bendrauk natūraliai, draugiškai ir neformaliai.
Atsakyk praktiškai ir ne per ilgai.

Tau pateikiamas paskutinių grupės pokalbių kontekstas.
Naudok jį, kad suprastum, apie ką grupės nariai kalba.

Tu gali matyti tau perduotas nuotraukas ir screenshotus.
Analizuok jų turinį kartu su žmogaus parašytu tekstu.

Tu turi interneto paieškos įrankį.

Kai klausimas priklauso nuo naujausios ar besikeičiančios
informacijos, pavyzdžiui:
- dabartiniai orai ir prognozės,
- skrydžių laikai ir pakeitimai,
- viešbučių informacija,
- kainos,
- restoranai,
- darbo laikas,
- naujienos,
- valiutų kursai,
- kita aktuali informacija,

naudok interneto paiešką pats.
Žmogui nereikia pateikti nuorodos.

Jeigu informaciją tikrinai internete, remkis tuo, ką radai.
Neišgalvok faktų, kurių nežinai.

Tu matai naujas grupės tekstines žinutes ir nuotraukas,
tačiau neturi atsakyti į kiekvieną jų.

Atsakyk tik tada, kai žmogus aiškiai kreipiasi į Robą,
pvz. parašo „Roba“ arba pamini tavo Telegram vartotojo vardą.

Kai atsakai, elkis kaip normalus grupės dalyvis,
o ne kaip formalus klientų aptarnavimo botas.
"""


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
        headers={"Content-Type": "application/json"},
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


def send_message(
    chat_id,
    text,
    reply_to_message_id=None
):
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


def get_telegram_photo_base64(file_id):
    """
    Parsisiunčia Telegram nuotrauką ir paverčia
    ją į base64 data URL, kurį supranta OpenAI.
    """

    file_info = telegram_api(
        "getFile",
        {
            "file_id": file_id
        }
    )

    file_path = (
        file_info
        .get("result", {})
        .get("file_path")
    )

    if not file_path:
        raise RuntimeError(
            "Telegram negrazino file_path."
        )

    file_url = (
        "https://api.telegram.org/file/"
        f"bot{TELEGRAM_TOKEN}/"
        f"{file_path}"
    )

    with urllib.request.urlopen(
        file_url,
        timeout=30
    ) as response:
        image_bytes = response.read()

    encoded = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    extension = (
        file_path
        .split(".")[-1]
        .lower()
    )

    if extension == "png":
        mime_type = "image/png"
    elif extension == "webp":
        mime_type = "image/webp"
    else:
        mime_type = "image/jpeg"

    return (
        f"data:{mime_type};base64,"
        f"{encoded}"
    )


def process_message(
    chat_id,
    message_id,
    name,
    text,
    photo_file_id=None
):
    try:

        print(
            f"Gauta Telegram zinute: "
            f"{name}: {text} "
            f"Photo: {bool(photo_file_id)}",
            flush=True
        )

        #
        # Įsimenam žinutę pokalbio kontekstui
        #

        history_text = text

        if photo_file_id:
            if history_text:
                history_text += " [atsiuntė nuotrauką]"
            else:
                history_text = "[atsiuntė nuotrauką]"

        history[chat_id].append(
            f"{name}: {history_text}"
        )

        lower_text = text.lower()

        called_roba = (
            "roba" in lower_text
            or "@robacaboverde_bot" in lower_text
        )

        #
        # Jei Roba nepaminėtas,
        # žinutę tik išsaugom kontekstui.
        #

        if not called_roba:
            print(
                "Roba nepaminetas - "
                "zinute tik isiminta.",
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

        #
        # Formuojam tekstą OpenAI
        #

        prompt_text = (
            "Paskutinis grupės "
            "pokalbio kontekstas:\n\n"
            f"{conversation}\n\n"
            "Dabar atsakyk į "
            "naujausią žinutę:\n"
            f"{name}: {text}"
        )

        #
        # OpenAI input.
        # Jei yra nuotrauka, pridedam input_image.
        #

        content = [
            {
                "type": "input_text",
                "text": prompt_text
            }
        ]

        if photo_file_id:

            print(
                "Parsiunciama Telegram nuotrauka...",
                flush=True
            )

            image_data_url = (
                get_telegram_photo_base64(
                    photo_file_id
                )
            )

            content.append(
                {
                    "type": "input_image",
                    "image_url": image_data_url,
                    "detail": "auto"
                }
            )

            print(
                "Nuotrauka prideta prie OpenAI uzklausos.",
                flush=True
            )

        #
        # OpenAI + web search + vision
        #

        response = client.responses.create(
            model="gpt-5.6-luna",

            tools=[
                {
                    "type": "web_search"
                }
            ],

            tool_choice="auto",

            instructions=SYSTEM_PROMPT,

            input=[
                {
                    "role": "user",
                    "content": content
                }
            ],
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
            f"ROBOS KLAIDA: "
            f"{type(e).__name__}: {e}",
            flush=True
        )

        try:
            send_message(
                chat_id,
                "Roba dabar susidūrė su "
                "technine klaida 😅 "
                "Pabandyk dar kartą.",
                message_id
            )

        except Exception as send_error:

            print(
                "Nepavyko issiusti "
                "klaidos zinutes: "
                f"{send_error}",
                flush=True
            )


@web.route("/")
def home():
    return "Roba Cabo Verde veikia 🦈"


@web.route("/health")
def health():
    return "OK"


@web.route(
    "/telegram",
    methods=["POST"]
)
def telegram_webhook():

    try:

        data = request.get_json(
            force=True,
            silent=False
        )

        print(
            "Telegram webhook gautas. "
            f"Update ID: "
            f"{data.get('update_id')}",
            flush=True
        )

        message = (
            data.get("message")
            or data.get("edited_message")
        )

        if not message:
            return "OK", 200

        user = message.get(
            "from",
            {}
        )

        if user.get("is_bot"):
            return "OK", 200

        chat = message.get(
            "chat",
            {}
        )

        chat_id = chat.get("id")

        message_id = message.get(
            "message_id"
        )

        if not chat_id:
            return "OK", 200

        name = (
            user.get("first_name")
            or user.get("username")
            or "Dalyvis"
        )

        #
        # Tekstas arba nuotraukos caption
        #

        text = (
            message.get("text")
            or message.get("caption")
            or ""
        ).strip()

        #
        # Telegram nuotrauka.
        # Telegram pateikia kelis dydžius.
        # Imam paskutinį - didžiausią.
        #

        photos = message.get(
            "photo",
            []
        )

        photo_file_id = None

        if photos:
            photo_file_id = (
                photos[-1]
                .get("file_id")
            )

        #
        # Jei nėra nei teksto,
        # nei nuotraukos - kol kas ignoruojam.
        #

        if not text and not photo_file_id:
            return "OK", 200

        thread = threading.Thread(
            target=process_message,
            args=(
                chat_id,
                message_id,
                name,
                text,
                photo_file_id
            ),
            daemon=True
        )

        thread.start()

        return "OK", 200

    except Exception as e:

        print(
            f"WEBHOOK KLAIDA: "
            f"{type(e).__name__}: {e}",
            flush=True
        )

        return "OK", 200


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
            f"Webhook nustatytas: "
            f"{result}",
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
