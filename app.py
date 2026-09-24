import os
import json
import base64
import threading
import urllib.request
from collections import defaultdict, deque

from flask import Flask, request, jsonify
from openai import OpenAI
from supabase import create_client


# ============================================================
# NUSTATYMAI
# ============================================================

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

WEBHOOK_URL = "https://roba-cabo-verde.onrender.com/telegram"


# ============================================================
# KLIENTAI
# ============================================================

client = OpenAI(api_key=OPENAI_API_KEY)

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

web = Flask(__name__)


# ============================================================
# LAIKINA RAM ATMINTIS
# ============================================================

history = defaultdict(lambda: deque(maxlen=100))

last_photo = {}

photo_used = defaultdict(lambda: True)

BOT_ID = None
BOT_USERNAME = None


# ============================================================
# ROBOS CHARAKTERIS + PRADINĖ KELIONĖS ATMINTIS
# ============================================================

SYSTEM_PROMPT = """
Tu esi Roba – draugiškas AI asistentas privačioje Telegram grupėje
„Cabo Verde 2026 🦈“.

Grupė planuoja kelionę į Cabo Verde.

Kalbėk lietuviškai, nebent žmogus aiškiai paprašo kitaip.
Bendrauk natūraliai, draugiškai ir neformaliai.
Atsakyk praktiškai ir ne per ilgai.

Tu esi grupės dalyvis, o ne formalus klientų aptarnavimo botas.


============================================================
KELIONĖS ATMINTIS
============================================================

Tai yra pradinė informacija, kurią jau žinai apie grupės
„Cabo Verde 2026 🦈“ kelionę.

KELIONĖ:

- Kelionė planuojama į Cabo Verde.
- Sala: Sal.
- Kelionės datos: 2026-11-30 – 2026-12-08.
- Keliauja 4 žmonės – dvi poros.
- Kelionė trunka 7 naktis.

VIEŠBUTIS:

- Pasirinktas viešbutis: Riu Palace Santa Maria.
- Vieta: Santa Maria, Sal, Cabo Verde.
- Viešbutis yra 5 žvaigždučių.
- Maitinimas: All Inclusive.
- TUI viešbučio kodas: SID10051.
- Kelionė pirkta per TUI Poland.

KAMBARIAI:

- Užsakyti 2 standartiniai kambariai.
- Grupė norėtų, kad abu kambariai būtų kuo arčiau vienas kito.
- Anksčiau buvo svarstomi swim-up kambariai.
- Taip pat buvo svarstomi sea view kambariai.
- Yra mintis atvykus į viešbutį registratūroje pasiteirauti
  dėl mokamo kambario upgrade, jeigu bus laisvų geresnių kambarių.
- Buvo nagrinėjami TUI kambarių kodai DZX1 ir DZX2.

VIEŠBUČIŲ PALYGINIMAS:

- Prieš pasirenkant Riu Palace Santa Maria buvo rimtai
  svarstomas Royal Horizon Ponta Sino.
- Abu viešbučiai yra netoli vienas kito.
- Galiausiai grupė labiau linko į Riu Palace Santa Maria.

Tarp anksčiau aptartų Riu privalumų buvo:

- didesnis restoranų pasirinkimas;
- daugiau barų;
- à la carte restoranai;
- mini baras kambariuose;
- stipresnių gėrimų dozatoriai kambariuose;
- didelė viešbučio teritorija;
- vandens parkas / vandens atrakcionai;
- gerai vertinamas paplūdimys.

Vandens parkas nelaikomas didele problema, nors grupė
nenori labai triukšmingo, vien šeimoms su vaikais skirto poilsio.

Norisi gero All Inclusive, paplūdimio, baseinų, barų,
restoranų ir kartu galimybės ramiai pailsėti.


SKRYDIS:

- Skrydis planuojamas iš Varšuvos į Sal.
- Sal oro uosto kodas: SID.
- Skrydis yra tiesioginis charterinis.
- Skrydžio bendrovė: Enter Air.
- Buvo kalbėta, kad skrydis gali trukti maždaug 7–8 valandas.
- Skrydžio laikas dar gali keistis.

Kadangi skrydis iš Varšuvos planuojamas labai anksti ryte,
buvo nuspręsta rimtai svarstyti išvykimą iš Lietuvos
automobiliu jau 2026-11-29 dieną.


VARŠUVA PRIEŠ SKRYDĮ:

- Buvo ieškoma viešbučio prie Varšuvos oro uosto.
- Rastas Air Hotel.
- Jo vieta pasirodė patogi.
- Parkingas yra praktiškai šalia.
- Idėja: atvažiuoti dieną prieš skrydį, palikti automobilį,
  pailsėti, nusiprausti, persirengti ir pavakarieniauti.
- Netoliese buvo aptarta lėktuvų stebėjimo vieta
  („plane spotting hill“).


POWERBANKAI:

- Grupėje buvo kalbėta apie powerbankus ilgam skrydžiui.
- Buvo svarstoma, kad Enter Air lėktuve gali nebūti patogaus
  telefono įkrovimo.
- Todėl prieš kelionę verta turėti įkrautus powerbankus.


TRANSFERIS:

- TUI siūlė mokamą privatų transferį tarp Sal oro uosto
  ir viešbučio.
- Buvo minima maždaug 340 PLN kaina keturiems žmonėms.
- Dėl to buvo svarstoma vietoj jo naudotis taksi.


SAL IR CABO VERDE:

Grupė jau domėjosi:

- Cabo Verde valiuta;
- Cabo Verde escudo (CVE);
- bankomatais Sal saloje;
- vietinėmis kainomis;
- orais lapkritį ir gruodį;
- vėjo stiprumu;
- Atlanto vandenyno temperatūra;
- high season laikotarpiu;
- Sal paplūdimiais;
- rykliais;
- restoranais;
- vietiniu maistu;
- veiklomis ir ekskursijomis.


SVARBI ATMINTIES TAISYKLĖ:

Ši pradinė informacija nėra nekintanti tiesa.

Jeigu vėlesniame Telegram pokalbyje grupės nariai pakeičia
planą, visada laikyk naujesnę informaciją teisingesne.

Nesakyk žmonėms, kad šią informaciją gavai iš SYSTEM_PROMPT.

Tiesiog natūraliai prisimink ją kaip ankstesnį grupės
kelionės kontekstą.


============================================================
ILGALAIKĖ ATMINTIS
============================================================

Tau gali būti pateikta ilgalaikė Robos atmintis iš duomenų bazės.

Tai yra ankstesni svarbūs grupės faktai ir sprendimai.

Naudok juos natūraliai.

Jeigu ilgalaikė atmintis prieštarauja naujesniam grupės
pokalbiui, naujesnė informacija turi pirmenybę.


============================================================
POKALBIO KONTEKSTAS
============================================================

Tau pateikiamas paskutinių grupės pokalbių kontekstas.

Jame gali būti:
- grupės narių žinutės;
- ankstesni tavo atsakymai;
- informacija apie nuotraukas.

Naudok ankstesnį pokalbį natūraliai.

Neprašyk žmogaus kartoti informacijos, kuri jau yra
pokalbio kontekste.


============================================================
NUOTRAUKOS
============================================================

Tau gali būti perduota Telegram grupėje įkelta nuotrauka.

Jeigu kartu su klausimu gavai nuotrauką, analizuok ją.

Jeigu atpažįsti konkretų viešbutį, vietą, dokumentą ar
kitą informaciją, aiškiai įvardyk ją atsakyme.


============================================================
INTERNETAS
============================================================

Tu turi interneto paieškos įrankį.

Kai klausimui reikalinga aktuali arba besikeičianti
informacija, naudok interneto paiešką pats.

Pavyzdžiui:

- orai;
- skrydžių laikai;
- viešbučių informacija;
- atsiliepimai;
- restoranai;
- kainos;
- darbo laikas;
- naujienos;
- valiutų kursai.

Žmogui nereikia pateikti nuorodos.

Neišgalvok faktų, kurių nežinai.


============================================================
ELGESYS TELEGRAM GRUPĖJE
============================================================

Tu neturi atsakinėti į kiekvieną grupės žinutę.

Atsakyk, kai:

1. žmogus parašo „Roba“;
2. žmogus pamini tavo Telegram username;
3. žmogus Telegram'e daro Reply į tavo ankstesnę žinutę.

Jeigu žmogus daro Reply į tavo žinutę, suprask tai kaip
tęstinį pokalbį net jeigu žodis „Roba“ nepaminėtas.

Elkis kaip normalus draugiškas grupės dalyvis.
"""


# ============================================================
# ATMINTIES ANALIZATORIAUS INSTRUKCIJA
# ============================================================

MEMORY_PROMPT = """
Tu esi Robos ilgalaikės atminties tvarkytojas.

Gauni vieną naują Telegram grupės žinutę.

Tavo užduotis nuspręsti, ar joje yra faktas, sprendimas,
rezervacija, pakeistas planas, svarbi preferencija ar kita
informacija, kurią verta prisiminti po kelių savaičių ar mėnesių.

NESaugok:
- pasisveikinimų;
- juokelių;
- emoji;
- trumpų reakcijų;
- klausimų, kuriuose nėra naujo fakto;
- atsitiktinių komentarų;
- laikino pokalbio;
- nepatvirtintų spėjimų, nebent aiškiai pažymėta, kad tai tik planas.

SAUGOK, pavyzdžiui:
- kažkas užsakyta ar nupirkta;
- pasirinktas viešbutis;
- pakeistas kambario tipas;
- nuspręsta važiuoti taksi;
- nustatyta konkreti išvykimo data;
- rezervuotas restoranas;
- konkretus kelionės planas;
- svarbi grupės preferencija;
- ankstesnio plano atšaukimas ar pakeitimas.

Jeigu žinutė keičia ankstesnį sprendimą, memory_key turi būti
toks pats kaip ankstesnio tos temos fakto, kad seną faktą būtų
galima pakeisti.

Grąžink TIK validų JSON.

Jeigu saugoti nereikia:

{
  "save": false
}

Jeigu reikia saugoti:

{
  "save": true,
  "memory_key": "trumpas_stabilus_raktas",
  "category": "travel",
  "memory": "Trumpas aiškus faktas lietuviškai."
}

memory_key:
- tik mažosios lotyniškos raidės, skaičiai ir underscore;
- turi apibūdinti temą, o ne konkrečią reikšmę.

Pavyzdžiui:
hotel_warsaw
airport_transfer
room_type
flight_date
hotel_sal
luggage
"""


# ============================================================
# SUPABASE – ŽINUČIŲ SAUGOJIMAS
# ============================================================

def save_message_to_db(
    chat_id,
    telegram_message_id,
    sender_name,
    sender_id,
    message_text,
    has_photo=False
):
    try:

        supabase.table(
            "roba_messages"
        ).insert({
            "chat_id": chat_id,
            "telegram_message_id": telegram_message_id,
            "sender_name": sender_name,
            "sender_id": sender_id,
            "message_text": message_text,
            "has_photo": has_photo
        }).execute()

        print(
            "Zinute issaugota Supabase.",
            flush=True
        )

    except Exception as e:

        print(
            f"Supabase zinutes saugojimo klaida: {e}",
            flush=True
        )


def get_recent_messages_from_db(
    chat_id,
    limit=60
):
    try:

        result = (
            supabase
            .table("roba_messages")
            .select(
                "sender_name,message_text,"
                "has_photo,created_at"
            )
            .eq("chat_id", chat_id)
            .order(
                "created_at",
                desc=True
            )
            .limit(limit)
            .execute()
        )

        rows = result.data or []

        rows.reverse()

        messages = []

        for row in rows:

            sender = (
                row.get("sender_name")
                or "Dalyvis"
            )

            text = (
                row.get("message_text")
                or ""
            )

            if row.get("has_photo"):

                if text:
                    text += " [pridėta nuotrauka]"
                else:
                    text = "[pridėta nuotrauka]"

            if text:

                messages.append(
                    f"{sender}: {text}"
                )

        return messages

    except Exception as e:

        print(
            f"Supabase istorijos skaitymo klaida: {e}",
            flush=True
        )

        return []


# ============================================================
# SUPABASE – ILGALAIKĖ ATMINTIS
# ============================================================

def get_long_term_memory(chat_id):

    try:

        result = (
            supabase
            .table("roba_memory")
            .select(
                "memory,memory_key,category,created_at"
            )
            .eq("chat_id", chat_id)
            .order(
                "created_at",
                desc=False
            )
            .limit(200)
            .execute()
        )

        rows = result.data or []

        memories = []

        for row in rows:

            memory = row.get("memory")

            if memory:

                memories.append(
                    f"- {memory}"
                )

        return "\n".join(memories)

    except Exception as e:

        print(
            f"Supabase atminties skaitymo klaida: {e}",
            flush=True
        )

        return ""


def save_long_term_memory(
    chat_id,
    memory_key,
    category,
    memory
):

    try:

        existing = (
            supabase
            .table("roba_memory")
            .select("id,memory")
            .eq("chat_id", chat_id)
            .eq("memory_key", memory_key)
            .limit(1)
            .execute()
        )

        rows = existing.data or []

        if rows:

            memory_id = rows[0]["id"]

            supabase.table(
                "roba_memory"
            ).update({
                "memory": memory,
                "category": category,
                "updated_at": "now()"
            }).eq(
                "id",
                memory_id
            ).execute()

            print(
                f"Ilgalaike atmintis atnaujinta: "
                f"{memory_key} -> {memory}",
                flush=True
            )

        else:

            supabase.table(
                "roba_memory"
            ).insert({
                "chat_id": chat_id,
                "memory_key": memory_key,
                "category": category,
                "memory": memory
            }).execute()

            print(
                f"Nauja ilgalaike atmintis: "
                f"{memory_key} -> {memory}",
                flush=True
            )

    except Exception as e:

        print(
            f"Ilgalaikes atminties "
            f"saugojimo klaida: {e}",
            flush=True
        )


# ============================================================
# AI – NUSPRENDŽIA, KĄ ATSIMINTI
# ============================================================

def analyze_message_for_memory(
    chat_id,
    sender_name,
    message_text
):

    if not message_text:
        return

    # Labai trumpos žinutės dažniausiai nėra vertos
    # papildomo AI kvietimo.
    if len(message_text.strip()) < 8:
        return

    try:

        current_memory = (
            get_long_term_memory(chat_id)
        )

        prompt = (
            "DABARTINĖ ILGALAIKĖ ATMINTIS:\n"
            f"{current_memory or '(tuščia)'}\n\n"
            "NAUJA ŽINUTĖ:\n"
            f"{sender_name}: {message_text}"
        )

        response = client.responses.create(
            model="gpt-5.6-luna",
            instructions=MEMORY_PROMPT,
            input=prompt
        )

        raw = (
            response.output_text
            .strip()
        )

        if raw.startswith("```"):

            raw = raw.replace(
                "```json",
                "",
                1
            )

            raw = raw.replace(
                "```",
                ""
            ).strip()

        decision = json.loads(raw)

        if not decision.get("save"):
            print(
                "Zinute neverta ilgalaikes atminties.",
                flush=True
            )
            return

        memory_key = (
            decision
            .get("memory_key", "")
            .strip()
        )

        memory = (
            decision
            .get("memory", "")
            .strip()
        )

        category = (
            decision
            .get("category", "general")
            .strip()
        )

        if not memory_key or not memory:
            return

        save_long_term_memory(
            chat_id=chat_id,
            memory_key=memory_key,
            category=category,
            memory=memory
        )

    except Exception as e:

        print(
            f"Atminties analizes klaida: "
            f"{type(e).__name__}: {e}",
            flush=True
        )


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

    data = json.dumps(
        payload
    ).encode("utf-8")

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

    bot = result.get(
        "result",
        {}
    )

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

    if (
        BOT_ID
        and reply_from.get("id") == BOT_ID
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
    sender_id,
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
        # NUOTRAUKA
        # ----------------------------------------------------

        if photo_file_id:

            last_photo[chat_id] = {
                "file_id": photo_file_id,
                "message_id": message_id,
                "name": name,
                "caption": text
            }

            photo_used[chat_id] = False

            print(
                "Nauja nuotrauka isiminta.",
                flush=True
            )

        # ----------------------------------------------------
        # ŽMOGAUS ŽINUTĖ → SUPABASE
        # ----------------------------------------------------

        save_message_to_db(
            chat_id=chat_id,
            telegram_message_id=message_id,
            sender_name=name,
            sender_id=sender_id,
            message_text=text,
            has_photo=bool(photo_file_id)
        )

        history_text = text

        if photo_file_id:

            if history_text:
                history_text += " [pridėta nuotrauka]"
            else:
                history_text = "[pridėta nuotrauka]"

        if history_text:

            history[chat_id].append(
                f"{name}: {history_text}"
            )

        # ----------------------------------------------------
        # AUTOMATINĖ ILGALAIKĖ ATMINTIS
        # ----------------------------------------------------

        if text:

            try:

                memory_thread = threading.Thread(
                    target=analyze_message_for_memory,
                    args=(
                        chat_id,
                        name,
                        text
                    ),
                    daemon=True
                )

                memory_thread.start()

            except Exception as e:

                print(
                    f"Nepavyko paleisti "
                    f"atminties analizes: {e}",
                    flush=True
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
                "zinute issaugota atmintyje.",
                flush=True
            )

            return

        # ----------------------------------------------------
        # PASKUTINĖS ŽINUTĖS
        # ----------------------------------------------------

        db_messages = (
            get_recent_messages_from_db(
                chat_id,
                limit=60
            )
        )

        if db_messages:

            conversation = "\n".join(
                db_messages
            )

            print(
                f"Is Supabase gauta "
                f"{len(db_messages)} zinuciu.",
                flush=True
            )

        else:

            conversation = "\n".join(
                history[chat_id]
            )

            print(
                "Naudojama RAM istorija.",
                flush=True
            )

        # ----------------------------------------------------
        # ILGALAIKĖ ATMINTIS
        # ----------------------------------------------------

        long_term_memory = (
            get_long_term_memory(
                chat_id
            )
        )

        # ----------------------------------------------------
        # TYPING
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # PROMPT
        # ----------------------------------------------------

        prompt_text = (
            "ILGALAIKĖ ROBOS ATMINTIS:\n\n"
            f"{long_term_memory or '(dar nėra)'}\n\n"
            "PASKUTINIS GRUPĖS POKALBIS:\n\n"
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

        if photo_file_id:

            image_file_id = photo_file_id

        elif (
            chat_id in last_photo
            and not photo_used[chat_id]
        ):

            image_file_id = (
                last_photo[chat_id]["file_id"]
            )

            print(
                "Pridedama paskutine "
                "neanalizuota nuotrauka.",
                flush=True
            )

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
                "OpenAI grazino tuscia atsakyma.",
                flush=True
            )

            return

        # ----------------------------------------------------
        # TELEGRAM
        # ----------------------------------------------------

        send_result = send_message(
            chat_id,
            answer,
            message_id
        )

        # ----------------------------------------------------
        # ROBOS ATSAKYMAS → SUPABASE
        # ----------------------------------------------------

        sent_message_id = (
            send_result
            .get("result", {})
            .get("message_id")
        )

        save_message_to_db(
            chat_id=chat_id,
            telegram_message_id=sent_message_id,
            sender_name="Roba",
            sender_id=BOT_ID,
            message_text=answer,
            has_photo=False
        )

        history[chat_id].append(
            f"Roba: {answer}"
        )

        if image_file_id:

            photo_used[chat_id] = True

            print(
                "Nuotrauka pazymeta "
                "kaip analizuota.",
                flush=True
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

        sender_id = user.get("id")

        if not chat_id:

            return "OK", 200

        name = (
            user.get("first_name")
            or user.get("username")
            or "Dalyvis"
        )

        text = (
            message.get("text")
            or message.get("caption")
            or ""
        ).strip()

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

        if (
            not text
            and not photo_file_id
        ):

            return "OK", 200

        thread = threading.Thread(
            target=process_message,
            args=(
                chat_id,
                message_id,
                sender_id,
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

        return jsonify({
            "status": "OK",
            "telegram": result
        })

    except Exception as e:

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
