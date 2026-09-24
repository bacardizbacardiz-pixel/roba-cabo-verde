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


# ============================================================
# ATMINTIS
# ============================================================

# Paskutinės 100 grupės pokalbio žinučių.
# Saugomos žmonių žinutės ir Robos atsakymai.
history = defaultdict(lambda: deque(maxlen=100))

# Paskutinė grupėje įkelta nuotrauka.
last_photo = {}

# Ar paskutinė nuotrauka jau buvo perduota Robai.
# False = dar neanalizuota.
photo_used = defaultdict(lambda: True)

BOT_ID = None
BOT_USERNAME = None


SYSTEM_PROMPT = """
Tu esi Roba – draugiškas AI asistentas privačioje Telegram grupėje
„Cabo Verde 2026 🦈“.

Grupė planuoja kelionę į Cabo Verde.

Kalbėk lietuviškai, nebent žmogus aiškiai paprašo kitaip.
Bendrauk natūraliai, draugiškai ir neformaliai.
Atsakyk praktiškai ir ne per ilgai.

POKALBIO KONTEKSTAS:

Tau pateikiamas paskutinių grupės pokalbių kontekstas.
Jame yra grupės narių žinutės ir ankstesni tavo paties atsakymai.

Naudok ankstesnį pokalbį natūraliai.

Jeigu prieš tai kalbėjote apie konkretų viešbutį, vietą,
skrydį, restoraną, nuotrauką ar kitą objektą, suprask tokius
tęsinius kaip:

„o ką apie jį manai?“
„o kaip ten paplūdimys?“
„papasakok daugiau“
„o kiek kainuoja?“
„o kaip maistas?“
„ar verta?“
„o ten toli?“

Neprašyk žmogaus kartoti informacijos, kuri jau yra pokalbio
kontekste.

NUOTRAUKOS:

Tau gali būti perduota Telegram grupėje įkelta nuotrauka.

Jeigu kartu su klausimu gavai nuotrauką, analizuok ją ir
naudok jos informaciją atsakymui.

Jeigu nuotraukoje atpažįsti konkretų objektą, viešbutį,
vietą, dokumentą ar kitą informaciją, aiškiai įvardyk ją
atsakyme. Tada ši informacija taps tolesnio pokalbio kontekstu.

INTERNETAS:

Tu turi interneto paieškos įrankį.

Kai klausimui reikalinga aktuali arba besikeičianti
informacija, naudok interneto paiešką pats.

Pavyzdžiui:
- orai ir prognozės,
- skrydžių laikai,
- viešbučių informacija,
- viešbučių atsiliepimai,
- restoranai,
- kainos,
- darbo laikas,
- naujienos,
- valiutų kursai,
- kelionių informacija.

Jeigu žmogus klausia, ką manai apie konkretų viešbutį,
gali pats internete patikrinti jo informaciją, atsiliepimus,
vietą, paplūdimį, maistą ar kitus aktualius faktus.

Žmogui nereikia pateikti nuorodos.

Neišgalvok faktų, kurių nežinai.

ELGESYS TELEGRAM GRUPĖJE:

Tu neturi atsakinėti į kiekvieną grupės žinutę.

Atsakyk, kai:
1. žmogus parašo „Roba“;
2. žmogus pamini tavo Telegram username;
3. žmogus Telegram'e daro Reply į tavo ankstesnę žinutę.

Jeigu žmogus daro Reply į tavo žinutę, suprask tai kaip
tęstinį pokalbį net jeigu žodis „Roba“ nepaminėtas.

Elkis kaip normalus draugiškas grupės dalyvis,
o ne kaip formalus klientų aptarnavimo botas.
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


def get_bot_identity():

    global BOT_ID
    global BOT_USERNAME

    if BOT_ID is not None:
        return

    result = telegram_api("getMe")

    bot = result.get("result", {})

    BOT_ID = bot.get("id")

    username = bot.get("username")

    if username:
        BOT_USERNAME = username.lower()

    print(
        f"Telegram botas: "
        f"ID={BOT_ID}, "
        f"username={BOT_USERNAME}",
        flush=True
    )


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


# ============================================================
# NUOTRAUKOS
# ============================================================

def get_telegram_photo_base64(file_id):

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


# ============================================================
# REPLY Į ROBĄ
# ============================================================

def is_reply_to_roba(message):

    reply = message.get(
        "reply_to_message"
    )

    if not reply:
        return False

    reply_from = reply.get(
        "from",
        {}
    )

    reply_user_id = reply_from.get(
        "id"
    )

    if (
        BOT_ID
        and reply_user_id == BOT_ID
    ):
        return True

    reply_username = (
        reply_from
        .get("username", "")
        .lower()
    )

    if (
        BOT_USERNAME
        and reply_username == BOT_USERNAME
    ):
        return True

    return False


def get_reply_context(message):

    reply = message.get(
        "reply_to_message"
    )

    if not reply:
        return ""

    reply_text = (
        reply.get("text")
        or reply.get("caption")
        or ""
    )

    if not reply_text:
        return ""

    reply_from = reply.get(
        "from",
        {}
    )

    reply_name = (
        reply_from.get("first_name")
        or reply_from.get("username")
        or "Nežinomas"
    )

    return (
        "\nŽmogus Telegram'e daro Reply "
        "į šią žinutę:\n"
        f"{reply_name}: {reply_text}\n"
    )


# ============================================================
# PAGRINDINIS ŽINUTĖS APDOROJIMAS
# ============================================================

def process_message(
    chat_id,
    message_id,
    name,
    text,
    photo_file_id,
    replied_to_roba,
    reply_context
):

    try:

        print(
            f"Gauta Telegram zinute: "
            f"{name}: {text} "
            f"Photo: {bool(photo_file_id)} "
            f"ReplyToRoba: {replied_to_roba}",
            flush=True
        )

        # ----------------------------------------------------
        # NAUJA NUOTRAUKA
        # ----------------------------------------------------

        if photo_file_id:

            last_photo[chat_id] = {
                "file_id": photo_file_id,
                "message_id": message_id,
                "name": name,
                "caption": text
            }

            # Šios nuotraukos Roba dar nematė.
            photo_used[chat_id] = False

            print(
                "Nauja nuotrauka isiminta. "
                "Ji dar neanalizuota.",
                flush=True
            )

        # ----------------------------------------------------
        # ŽMOGAUS ŽINUTĖ → ISTORIJA
        # ----------------------------------------------------

        history_text = text

        if photo_file_id:

            if history_text:

                history_text += (
                    " [pridėta nuotrauka]"
                )

            else:

                history_text = (
                    "[pridėta nuotrauka]"
                )

        if history_text:

            history[chat_id].append(
                f"{name}: {history_text}"
            )

        # ----------------------------------------------------
        # AR ROBĄ KVIEČIA?
        # ----------------------------------------------------

        lower_text = text.lower()

        called_by_name = (
            "roba" in lower_text
        )

        called_by_username = False

        if BOT_USERNAME:

            called_by_username = (
                f"@{BOT_USERNAME}"
                in lower_text
            )

        should_answer = (
            called_by_name
            or called_by_username
            or replied_to_roba
        )

        if not should_answer:

            print(
                "Roba nekviestas - "
                "zinute tik isiminta.",
                flush=True
            )

            return

        # ----------------------------------------------------
        # POKALBIO KONTEKSTAS
        # ----------------------------------------------------

        conversation = "\n".join(
            history[chat_id]
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

        prompt_text = (
            "Paskutinis grupės pokalbio "
            "kontekstas:\n\n"
            f"{conversation}\n"
            f"{reply_context}\n"
            "Atsakyk į naujausią "
            "žmogaus žinutę:\n"
            f"{name}: {text}"
        )

        content = [
            {
                "type": "input_text",
                "text": prompt_text
            }
        ]

        # ----------------------------------------------------
        # NUOTRAUKOS LOGIKA
        # ----------------------------------------------------

        image_file_id = None

        # Jeigu Roba kviečiamas žinute,
        # prie kurios tiesiogiai pridėta nuotrauka.
        if photo_file_id:

            image_file_id = photo_file_id

        # SVARBIAUSIAS PAKEITIMAS:
        #
        # Jeigu prieš tai grupėje buvo įkelta nuotrauka
        # ir Roba jos dar neanalizavo, pirmas kitas
        # kreipinys į Robą automatiškai gauna nuotrauką.
        #
        # Jokių raktažodžių.
        elif (
            chat_id in last_photo
            and not photo_used[chat_id]
        ):

            image_file_id = (
                last_photo[chat_id]["file_id"]
            )

            print(
                "Prie pirmo kreipinio "
                "pridedama paskutine "
                "neanalizuota nuotrauka.",
                flush=True
            )

        # ----------------------------------------------------
        # NUOTRAUKA → OPENAI
        # ----------------------------------------------------

        if image_file_id:

            print(
                "Parsiunciama Telegram "
                "nuotrauka...",
                flush=True
            )

            image_data_url = (
                get_telegram_photo_base64(
                    image_file_id
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
                "Nuotrauka prideta prie "
                "OpenAI uzklausos.",
                flush=True
            )

        # ----------------------------------------------------
        # OPENAI
        # ----------------------------------------------------

        print(
            "Kreipiamasi i OpenAI...",
            flush=True
        )

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

        answer = (
            response
            .output_text
            .strip()
        )

        if not answer:

            print(
                "OpenAI grazino "
                "tuscia atsakyma.",
                flush=True
            )

            return

        # ----------------------------------------------------
        # TELEGRAM ATSAKYMAS
        # ----------------------------------------------------

        send_result = send_message(
            chat_id,
            answer,
            message_id
        )

        # ----------------------------------------------------
        # ROBOS ATSAKYMAS → ISTORIJA
        # ----------------------------------------------------

        history[chat_id].append(
            f"Roba: {answer}"
        )

        # Jeigu prie šio atsakymo siuntėme nuotrauką,
        # laikome, kad Roba ją jau išanalizavo.
        if image_file_id:

            photo_used[chat_id] = True

            print(
                "Nuotrauka pazymeta "
                "kaip analizuota.",
                flush=True
            )

        sent_message_id = (
            send_result
            .get("result", {})
            .get("message_id")
        )

        print(
            f"Roba atsake i Telegram. "
            f"Message ID: {sent_message_id}",
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


# ============================================================
# WEB
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

@web.route(
    "/telegram",
    methods=["POST"]
)
def telegram_webhook():

    try:

        get_bot_identity()

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

        # ----------------------------------------------------
        # TEKSTAS / CAPTION
        # ----------------------------------------------------

        text = (
            message.get("text")
            or message.get("caption")
            or ""
        ).strip()

        # ----------------------------------------------------
        # NUOTRAUKA
        # ----------------------------------------------------

        photos = message.get(
            "photo",
            []
        )

        photo_file_id = None

        if photos:

            # Telegram pateikia kelias tos pačios
            # nuotraukos rezoliucijas.
            # Imam didžiausią.
            photo_file_id = (
                photos[-1]
                .get("file_id")
            )

        # ----------------------------------------------------
        # REPLY
        # ----------------------------------------------------

        replied_to_roba = (
            is_reply_to_roba(
                message
            )
        )

        reply_context = (
            get_reply_context(
                message
            )
        )

        # ----------------------------------------------------
        # NIEKO NAUDINGO
        # ----------------------------------------------------

        if (
            not text
            and not photo_file_id
        ):

            return "OK", 200

        # ----------------------------------------------------
        # BACKGROUND
        # ----------------------------------------------------

        thread = threading.Thread(
            target=process_message,
            args=(
                chat_id,
                message_id,
                name,
                text,
                photo_file_id,
                replied_to_roba,
                reply_context
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


# ============================================================
# WEBHOOK SETUP
# ============================================================

@web.route("/setup-webhook")
def setup_webhook():

    try:

        get_bot_identity()

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


# ============================================================
# WEBHOOK INFO
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
