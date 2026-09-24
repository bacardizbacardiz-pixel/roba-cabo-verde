import os
import json
import base64
import re
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
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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
# ROBOS SISTEMINIS PROMPT
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

Kelionė:
- Sal, Cabo Verde.
- 2026-11-30 – 2026-12-08.
- 4 žmonės – dvi poros.
- 7 naktys.

Viešbutis:
- Riu Palace Santa Maria.
- Santa Maria, Sal.
- 5 žvaigždutės.
- All Inclusive.
- TUI Poland.
- TUI kodas SID10051.

Kambariai:
- Užsakyti 2 standartiniai kambariai.
- Norima kambarių kuo arčiau vienas kito.
- Buvo svarstomi swim-up ir sea view kambariai.
- Atvykus galima teirautis mokamo upgrade.
- Buvo nagrinėjami DZX1 ir DZX2.

Skrydis:
- Varšuva → Sal (SID).
- Tiesioginis charterinis.
- Enter Air.
- Maždaug 7–8 valandos.
- Skrydžio laikas gali keistis.

Varšuva:
- Nakvynė planuojama prieš skrydį.
- Ankstesniuose pokalbiuose buvo svarstomas Air Hotel.
- Vėlesnė ilgalaikė atmintis turi pirmenybę prieš šį
  pradinį kontekstą.

Transferis:
- TUI siūlė privatų transferį maždaug už 340 PLN
  keturiems žmonėms.
- Buvo svarstomas taksi.

Grupė taip pat domėjosi:
- Cabo Verde escudo;
- bankomatais;
- orais;
- jūros temperatūra;
- vėju;
- paplūdimiais;
- rykliais;
- restoranais;
- ekskursijomis;
- vietiniu maistu.

SVARBU:
Jeigu naujesnis Telegram pokalbis arba ilgalaikė atmintis
prieštarauja šiam pradiniam kontekstui, naudok naujesnę
informaciją.


============================================================
ILGALAIKĖ ATMINTIS
============================================================

Tau gali būti pateikta ilgalaikė Robos atmintis iš Supabase.

Tai svarbūs ankstesni grupės faktai ir sprendimai.

Naudok juos natūraliai.

Naujesnė informacija turi pirmenybę prieš senesnę.


============================================================
POKALBIO KONTEKSTAS
============================================================

Tau pateikiamos paskutinės grupės žinutės.

Naudok jas kaip pokalbio kontekstą.

Neprašyk kartoti informacijos, kuri jau yra kontekste.


============================================================
NUOTRAUKOS
============================================================

Tau gali būti perduota Telegram nuotrauka arba screenshotas.

Analizuok tai, kas realiai matoma nuotraukoje.

Jeigu tai:
- rezervacija;
- TUI dokumentas;
- skrydžio informacija;
- viešbučio informacija;
- kambario informacija;
- bilietas;
- ekskursijos rezervacija;
- kaina;
- data;
- laikas;
- kitas kelionei svarbus dokumentas,

aiškiai perskaityk ir panaudok svarbią informaciją.

Neišgalvok neįskaitomų duomenų.


============================================================
INTERNETAS
============================================================

Tu turi interneto paieškos įrankį.

Kai reikalinga aktuali informacija, naudok interneto paiešką.

Pavyzdžiui:
- orai;
- skrydžiai;
- viešbučiai;
- kainos;
- restoranai;
- darbo laikas;
- valiutų kursai;
- naujienos.

Neišgalvok aktualių faktų.



============================================================
TODO SĄRAŠAS
============================================================

Grupė turi bendrą kelionės TODO sąrašą Supabase.

Kai programos logika pateikia TODO rezultatą, naudok tą rezultatą.
TODO darbai nėra tas pats, kas ilgalaikės kelionės faktų atmintis.

============================================================
ELGESYS TELEGRAM GRUPĖJE
============================================================

Atsakyk tik kai:

1. žmogus parašo „Roba“;
2. žmogus pamini tavo Telegram username;
3. žmogus daro Reply į tavo ankstesnę žinutę.

Kitais atvejais tylėk, tačiau grupės žinutės vis tiek
gali būti saugomos pokalbio istorijoje.
"""


# ============================================================
# TEKSTINĖS ATMINTIES PROMPT
# ============================================================

MEMORY_PROMPT = """
Tu esi Robos ilgalaikės atminties tvarkytojas.

Gauni naują Telegram grupės žinutę.

Nuspręsk, ar joje yra faktas, sprendimas, rezervacija,
pakeistas planas, svarbi preferencija ar kita informacija,
kurią verta prisiminti po kelių savaičių ar mėnesių.

NESaugok:
- pasisveikinimų;
- juokelių;
- emoji;
- trumpų reakcijų;
- paprastų klausimų;
- laikino pokalbio;
- nereikšmingų komentarų.

SAUGOK:
- rezervacijas;
- pirkimus;
- pasirinktą viešbutį;
- kambario pakeitimus;
- transporto sprendimus;
- datas;
- skrydžio informaciją;
- ekskursijas;
- konkrečius kelionės planus;
- svarbias preferencijas;
- ankstesnio plano pakeitimą ar atšaukimą.

Jeigu nauja žinutė keičia ankstesnį faktą, naudok tą patį
memory_key.

Grąžink TIK validų JSON.

Jeigu saugoti nereikia:

{
  "save": false
}

Jeigu reikia:

{
  "save": true,
  "memory_key": "stabilus_raktas",
  "category": "travel",
  "memory": "Trumpas aiškus faktas lietuviškai."
}

memory_key naudok mažosiomis lotyniškomis raidėmis,
skaičiais ir underscore.

Pavyzdžiai:
hotel_warsaw
airport_transfer
room_type
flight_outbound
flight_return
excursion_sal
luggage
"""


# ============================================================
# NUOTRAUKOS ATMINTIES PROMPT
# ============================================================

IMAGE_MEMORY_PROMPT = """
Tu esi Robos ilgalaikės atminties tvarkytojas.

Tau pateikiama Telegram grupėje įkelta nuotrauka arba
screenshotas, kurį žmogus paprašė Robos pažiūrėti.

Iš nuotraukos išrink TIK kelionei ilgalaikę reikšmę turinčius
aiškiai matomus faktus.

Pavyzdžiui:
- skrydžio data ir laikas;
- skrydžio numeris;
- oro uostai;
- oro linijos;
- viešbutis;
- kambario tipas;
- rezervacijos datos;
- transferis;
- ekskursija;
- rezervacijos būsena;
- konkreti sumokėta ar užsakyta paslauga.

NESaugok:
- reklaminio teksto;
- atsitiktinių vaizdo detalių;
- neaiškiai matomos informacijos;
- spėjimų;
- paprastos atostogų nuotraukos aprašymo.

Jeigu nuotraukoje nėra aiškaus ilgalaikio kelionės fakto,
grąžink:

{
  "memories": []
}

Jeigu yra, grąžink:

{
  "memories": [
    {
      "memory_key": "stabilus_raktas",
      "category": "travel",
      "memory": "Trumpas aiškus faktas lietuviškai."
    }
  ]
}

Vienoje nuotraukoje gali būti keli skirtingi svarbūs faktai.

Jeigu faktas keičia ankstesnę informaciją, naudok tokį patį
memory_key kaip tos temos ankstesniame įraše.

Grąžink TIK validų JSON.
"""



# ============================================================
# TODO AI PROMPT
# ============================================================

TODO_PROMPT = """
Tu esi Robos bendro Cabo Verde kelionės TODO sąrašo tvarkytojas.

Iš žmogaus žinutės nustatyk, ar jis nori:
- add: pridėti naują darbą;
- list: parodyti dar neatliktus darbus;
- complete: pažymėti darbą atliktu;
- delete: ištrinti darbą;
- none: žinutė nesusijusi su TODO sąrašo valdymu.

Svarbu:
- Įprastas klausimas apie kelionę nėra TODO komanda.
- "reikia", "nepamiršti", "įrašyk", "pridėk" gali reikšti add.
- "ką dar reikia padaryti", "parodyk sąrašą", "todo" gali reikšti list.
- "jau padarėm", "nupirkom", "atlikta", "sutvarkyta" gali reikšti complete.
- "ištrink", "pašalink" gali reikšti delete.
- task turi būti trumpas ir aiškus, be žodžio Roba.
- complete/delete atveju task turi apibūdinti, kurio esamo darbo ieškoti.

Grąžink TIK validų JSON.

{"action":"none"}

arba

{"action":"add","task":"Nupirkti powerbanką"}

arba

{"action":"list"}

arba

{"action":"complete","task":"powerbankas"}

arba

{"action":"delete","task":"powerbankas"}
"""

# ============================================================
# NEMOKAMAS TEKSTO ATMINTIES FILTRAS
# ============================================================

MEMORY_KEYWORDS = [
    "nusprend",
    "pasirink",
    "imam",
    "imsim",
    "imame",
    "neimam",
    "neimsim",
    "važiuosim",
    "vaziuosim",
    "skrisim",
    "vyksim",
    "sutarem",
    "sutarėm",
    "persigalvoj",
    "keičiam",
    "keiciam",
    "pakeit",
    "atšauk",
    "atsauk",
    "užsak",
    "uzsak",
    "rezerv",
    "nupirk",
    "pirkom",
    "sumok",
    "apmok",
    "biliet",
    "booking",
    "viešbut",
    "viesbut",
    "hotel",
    "kambar",
    "room",
    "skryd",
    "flight",
    "enter air",
    "tui",
    "transfer",
    "taksi",
    "taxi",
    "oro uost",
    "airport",
    "parking",
    "parkav",
    "lagamin",
    "bagaž",
    "bagaz",
    "powerbank",
    "restoran",
    "ekskurs",
    "kelion",
    "cabo verde",
    "cape verde",
    "santa maria",
    "riu",
    "novotel",
    "planuoj",
    "planas",
    "data",
    "išvyk",
    "isvyk",
    "atvyk",
    "nakvyn",
    "norim",
    "norėsim",
    "noresim",
    "labiau patinka",
    "patinka",
    "nenorim",
    "svarbu",
    "prioritet"
]


TRIVIAL_MESSAGES = {
    "ok",
    "oki",
    "okay",
    "gerai",
    "jo",
    "joo",
    "taip",
    "ne",
    "nu",
    "aha",
    "mhm",
    "aciu",
    "ačiū",
    "thanks",
    "super",
    "puiku",
    "lol",
    "haha",
    "hehe"
}


def should_analyze_for_memory(text):

    if not text:
        return False

    cleaned = text.strip()
    lower = cleaned.lower()

    if len(cleaned) < 8:
        return False

    normalized = re.sub(
        r"[^\wąčęėįšųūž]+",
        "",
        lower,
        flags=re.UNICODE
    )

    if normalized in TRIVIAL_MESSAGES:
        return False

    letters_or_numbers = re.findall(
        r"[A-Za-zĄČĘĖĮŠŲŪŽąčęėįšųūž0-9]",
        cleaned
    )

    if len(letters_or_numbers) < 4:
        return False

    keyword_hit = any(
        keyword in lower
        for keyword in MEMORY_KEYWORDS
    )

    if keyword_hit:
        return True

    has_date = bool(
        re.search(
            r"\b("
            r"\d{1,2}[./-]\d{1,2}"
            r"(?:[./-]\d{2,4})?"
            r"|20\d{2}[./-]\d{1,2}[./-]\d{1,2}"
            r")\b",
            cleaned
        )
    )

    if has_date:
        return True

    has_money = bool(
        re.search(
            r"\b\d+(?:[.,]\d+)?\s*"
            r"(?:€|eur|zl|pln|cve|usd|doler)",
            lower
        )
    )

    if has_money:
        return True

    has_time = bool(
        re.search(
            r"\b(?:[01]?\d|2[0-3])[:.][0-5]\d\b",
            lower
        )
    )

    if has_time:
        return True

    is_question = "?" in cleaned

    if not is_question and len(cleaned) >= 80:
        return True

    return False


# ============================================================
# SUPABASE – ŽINUČIŲ SAUGOJIMAS
# ============================================================

def save_message_to_db(
    chat_id,
    telegram_message_id,
    sender_name,
    sender_id,
    message_text,
    has_photo=False,
    photo_file_id=None
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
            "has_photo": has_photo,
            "photo_file_id": photo_file_id
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
                "has_photo,photo_file_id,created_at"
            )
            .eq("chat_id", chat_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        rows = result.data or []
        rows.reverse()

        messages = []

        for row in rows:

            sender = row.get("sender_name") or "Dalyvis"
            text = row.get("message_text") or ""

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


def get_last_photo_from_db(chat_id):

    try:

        result = (
            supabase
            .table("roba_messages")
            .select(
                "telegram_message_id,"
                "sender_name,message_text,"
                "photo_file_id,created_at"
            )
            .eq("chat_id", chat_id)
            .eq("has_photo", True)
            .not_.is_("photo_file_id", "null")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        rows = result.data or []

        if not rows:
            return None

        return rows[0]

    except Exception as e:

        print(
            f"Paskutines nuotraukos "
            f"paieskos klaida: {e}",
            flush=True
        )

        return None


# ============================================================
# SUPABASE – ILGALAIKĖ ATMINTIS
# ============================================================

def get_long_term_memory(chat_id):

    try:

        result = (
            supabase
            .table("roba_memory")
            .select(
                "memory,memory_key,category,"
                "created_at,updated_at"
            )
            .eq("chat_id", chat_id)
            .order("created_at", desc=False)
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
    memory,
    source_type="text",
    source_message_id=None
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

        data = {
            "memory": memory,
            "category": category,
            "source_type": source_type,
            "source_message_id": source_message_id,
            "updated_at": "now()"
        }

        if rows:

            memory_id = rows[0]["id"]

            supabase.table(
                "roba_memory"
            ).update(
                data
            ).eq(
                "id",
                memory_id
            ).execute()

            print(
                f"Ilgalaike atmintis atnaujinta: "
                f"{memory_key} -> {memory}",
                flush=True
            )

        else:

            data["chat_id"] = chat_id
            data["memory_key"] = memory_key

            supabase.table(
                "roba_memory"
            ).insert(
                data
            ).execute()

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
# TEKSTO ATMINTIES ANALIZĖ
# ============================================================

def analyze_message_for_memory(
    chat_id,
    sender_name,
    message_text,
    message_id
):

    if not message_text:
        return

    try:

        current_memory = get_long_term_memory(chat_id)

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

        raw = response.output_text.strip()

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
                "AI nusprende: zinute neverta "
                "ilgalaikes atminties.",
                flush=True
            )

            return

        memory_key = (
            decision.get("memory_key", "").strip()
        )

        memory = (
            decision.get("memory", "").strip()
        )

        category = (
            decision.get("category", "general").strip()
        )

        if not memory_key or not memory:
            return

        save_long_term_memory(
            chat_id=chat_id,
            memory_key=memory_key,
            category=category,
            memory=memory,
            source_type="text",
            source_message_id=message_id
        )

    except Exception as e:

        print(
            f"Atminties analizes klaida: "
            f"{type(e).__name__}: {e}",
            flush=True
        )



# ============================================================
# SUPABASE – TODO
# ============================================================

def get_todo_items(chat_id, status="open"):

    try:
        query = (
            supabase
            .table("roba_todo")
            .select("id,task,status,created_by,created_at,completed_at")
            .eq("chat_id", chat_id)
        )

        if status:
            query = query.eq("status", status)

        result = query.order("created_at", desc=False).execute()
        return result.data or []

    except Exception as e:
        print(f"TODO skaitymo klaida: {e}", flush=True)
        return []


def add_todo_item(chat_id, task, created_by):

    result = (
        supabase
        .table("roba_todo")
        .insert({
            "chat_id": chat_id,
            "task": task,
            "status": "open",
            "created_by": created_by
        })
        .execute()
    )

    return result.data or []


def normalize_todo_word(word):

    word = word.lower().strip()

    replacements = str.maketrans({
        "ą": "a",
        "č": "c",
        "ę": "e",
        "ė": "e",
        "į": "i",
        "š": "s",
        "ų": "u",
        "ū": "u",
        "ž": "z"
    })

    return word.translate(replacements)


def todo_word_stem(word):

    word = normalize_todo_word(word)

    # Paprastas lietuviškų galūnių trumpinimas.
    # Tikslas – kad, pvz., powerbanką / powerbankas,
    # nupirkti / nupirkom būtų atpažinti kaip artimi žodžiai.
    endings = [
        "omis", "uose", "uose", "imas", "ymas",
        "ame", "eme", "iai", "iai", "ius",
        "ais", "oms", "uos", "iai",
        "as", "is", "ys", "us", "os", "es",
        "ai", "ei", "ui", "am", "em",
        "om", "im", "iu",
        "a", "e", "i", "u", "o"
    ]

    for ending in endings:
        if word.endswith(ending) and len(word) - len(ending) >= 5:
            return word[:-len(ending)]

    return word


def find_best_todo_match(items, search_text):

    if not items:
        return None

    search_words = [
        todo_word_stem(word)
        for word in re.findall(
            r"[a-zA-ZąčęėįšųūžĄČĘĖĮŠŲŪŽ0-9]+",
            search_text.lower()
        )
        if len(word) >= 3
    ]

    if not search_words:
        return None

    best_item = None
    best_score = 0

    for item in items:

        task = (item.get("task") or "").lower()

        task_words = [
            todo_word_stem(word)
            for word in re.findall(
                r"[a-zA-ZąčęėįšųūžĄČĘĖĮŠŲŪŽ0-9]+",
                task
            )
            if len(word) >= 3
        ]

        score = 0

        for search_word in search_words:
            for task_word in task_words:

                if search_word == task_word:
                    score += 4
                    continue

                shorter = min(
                    len(search_word),
                    len(task_word)
                )

                if (
                    shorter >= 5
                    and (
                        search_word.startswith(task_word[:shorter])
                        or task_word.startswith(search_word[:shorter])
                    )
                ):
                    score += 2

                elif (
                    len(search_word) >= 6
                    and len(task_word) >= 6
                    and search_word[:6] == task_word[:6]
                ):
                    score += 2

        normalized_search = normalize_todo_word(search_text)
        normalized_task = normalize_todo_word(task)

        if normalized_search in normalized_task:
            score += 5

        if score > best_score:
            best_score = score
            best_item = item

    if best_score < 2:
        return None

    return best_item


def format_todo_list(items):

    if not items:
        return "TODO sąrašas tuščias 😎 Viskas padaryta!"

    lines = ["Mūsų Cabo Verde TODO 🦈"]

    for index, item in enumerate(items, start=1):
        lines.append(f"{index}. ⬜ {item.get('task')}")

    return "\n".join(lines)


def detect_todo_action(text, current_items):

    current_list = "\n".join(
        f"- {item.get('task')}"
        for item in current_items
    ) or "(sąrašas tuščias)"

    prompt = (
        "DABARTINIS NEATLIKTŲ DARBŲ SĄRAŠAS:\n"
        f"{current_list}\n\n"
        "NAUJA ŽINUTĖ:\n"
        f"{text}"
    )

    response = client.responses.create(
        model="gpt-5.6-luna",
        instructions=TODO_PROMPT,
        input=prompt
    )

    raw = response.output_text.strip()

    if raw.startswith("```"):
        raw = raw.replace("```json", "", 1)
        raw = raw.replace("```", "").strip()

    return json.loads(raw)


def handle_todo(chat_id, sender_name, text):

    try:
        current_items = get_todo_items(chat_id, "open")
        decision = detect_todo_action(text, current_items)

        action = decision.get("action", "none")
        task = (decision.get("task") or "").strip()

        if action == "none":
            return None

        if action == "list":
            return format_todo_list(current_items)

        if action == "add":

            if not task:
                return "Ką tiksliai įrašyti į TODO? 🙂"

            # Apsauga nuo akivaizdaus dublikato.
            for item in current_items:
                existing = (item.get("task") or "").strip().lower()

                if existing == task.lower():
                    return f"Šitas jau yra TODO sąraše 🙂\n⬜ {item.get('task')}"

            add_todo_item(
                chat_id=chat_id,
                task=task,
                created_by=sender_name
            )

            updated = get_todo_items(chat_id, "open")

            return (
                f"Įrašiau į TODO ✅\n"
                f"⬜ {task}\n\n"
                f"Dabar sąraše: {len(updated)}"
            )

        if action in ("complete", "delete"):

            if not task:
                return "Kurį TODO punktą turi omeny? 🙂"

            match = find_best_todo_match(
                current_items,
                task
            )

            if not match:
                return (
                    "Neradau tokio punkto dabartiniame TODO sąraše. "
                    "Parašyk „Roba, parodyk TODO“ ir pasirinksim tiksliau 🙂"
                )

            item_id = match["id"]
            item_task = match.get("task")

            if action == "complete":

                (
                    supabase
                    .table("roba_todo")
                    .update({
                        "status": "done",
                        "completed_at": "now()"
                    })
                    .eq("id", item_id)
                    .eq("chat_id", chat_id)
                    .execute()
                )

                remaining = get_todo_items(chat_id, "open")

                return (
                    f"Pažymėjau atlikta ✅\n"
                    f"~~{item_task}~~\n\n"
                    f"Liko darbų: {len(remaining)}"
                )

            (
                supabase
                .table("roba_todo")
                .delete()
                .eq("id", item_id)
                .eq("chat_id", chat_id)
                .execute()
            )

            return f"Ištryniau iš TODO 🗑️\n{item_task}"

        return None

    except Exception as e:
        print(
            f"TODO apdorojimo klaida: {type(e).__name__}: {e}",
            flush=True
        )
        return None


# ============================================================
# ILGALAIKĖS ATMINTIES PAMIRŠIMAS
# ============================================================

FORGET_PROMPT = """
Tu esi Robos ilgalaikės atminties tvarkytojas.

Žmogus aiškiai paprašė kažką PAMIRŠTI / IŠTRINTI iš Robos
ilgalaikės atminties.

Tau pateikiamas dabartinių atminties įrašų sąrašas su jų
memory_key ir tekstu.

Nustatyk, kurį VIENĄ atminties įrašą žmogus turi omeny.

Grąžink TIK validų JSON.

Jeigu radai aiškų atitikmenį:
{"memory_key":"tikslus_memory_key"}

Jeigu neaišku arba tinkamo įrašo nėra:
{"memory_key":null}
"""


def get_long_term_memory_rows(chat_id):

    try:
        result = (
            supabase
            .table("roba_memory")
            .select("id,memory_key,memory,category")
            .eq("chat_id", chat_id)
            .order("created_at", desc=False)
            .limit(200)
            .execute()
        )

        return result.data or []

    except Exception as e:
        print(
            f"Atminties irasu skaitymo klaida: {e}",
            flush=True
        )
        return []


def is_forget_request(text):

    lower = (text or "").lower()

    forget_words = [
        "pamiršk",
        "pamirsk",
        "užmiršk",
        "uzmirsk",
        "ištrink iš atminties",
        "istrink is atminties",
        "pašalink iš atminties",
        "pasalink is atminties"
    ]

    return any(word in lower for word in forget_words)


def handle_forget_request(chat_id, text):

    rows = get_long_term_memory_rows(chat_id)

    if not rows:
        return "Ilgalaikėje atmintyje nėra ką pamiršti 🙂"

    memory_list = "\n".join(
        f"- {row.get('memory_key')}: {row.get('memory')}"
        for row in rows
    )

    prompt = (
        "DABARTINĖ ATMINTIS:\n"
        f"{memory_list}\n\n"
        "ŽMOGAUS PRAŠYMAS:\n"
        f"{text}"
    )

    response = client.responses.create(
        model="gpt-5.6-luna",
        instructions=FORGET_PROMPT,
        input=prompt
    )

    raw = response.output_text.strip()

    if raw.startswith("```"):
        raw = raw.replace("```json", "", 1)
        raw = raw.replace("```", "").strip()

    decision = json.loads(raw)
    memory_key = decision.get("memory_key")

    if not memory_key:
        return (
            "Neradau vieno aiškaus atminties fakto, kurį reikėtų "
            "pamiršti. Parašyk truputį tiksliau 🙂"
        )

    match = next(
        (
            row for row in rows
            if row.get("memory_key") == memory_key
        ),
        None
    )

    if not match:
        return (
            "Tokio įrašo ilgalaikėje atmintyje neradau 🙂"
        )

    (
        supabase
        .table("roba_memory")
        .delete()
        .eq("chat_id", chat_id)
        .eq("memory_key", memory_key)
        .execute()
    )

    print(
        f"Ilgalaike atmintis istrinta: {memory_key}",
        flush=True
    )

    return (
        "Pamiršau ✅\n"
        f"{match.get('memory')}"
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

    bot = result.get("result", {})

    BOT_ID = bot.get("id")

    username = bot.get("username")

    if username:
        BOT_USERNAME = username.lower()

    print(
        f"Telegram botas: "
        f"ID={BOT_ID}, username={BOT_USERNAME}",
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
        f"bot{TELEGRAM_TOKEN}/{file_path}"
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
        file_path.split(".")[-1].lower()
    )

    if extension == "png":
        mime_type = "image/png"
    elif extension == "webp":
        mime_type = "image/webp"
    else:
        mime_type = "image/jpeg"

    return (
        f"data:{mime_type};base64,{encoded}"
    )


def analyze_image_for_memory(
    chat_id,
    image_data_url,
    source_message_id,
    user_question=""
):

    try:

        current_memory = get_long_term_memory(chat_id)

        prompt_text = (
            "DABARTINĖ ILGALAIKĖ ATMINTIS:\n"
            f"{current_memory or '(tuščia)'}\n\n"
            "ŽMOGAUS KLAUSIMAS / KOMENTARAS:\n"
            f"{user_question or '(nėra)'}\n\n"
            "Išanalizuok pridėtą nuotrauką ir nuspręsk, "
            "ar joje yra ilgalaikei kelionės atminčiai "
            "svarbių faktų."
        )

        response = client.responses.create(
            model="gpt-5.6-luna",
            instructions=IMAGE_MEMORY_PROMPT,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt_text
                        },
                        {
                            "type": "input_image",
                            "image_url": image_data_url,
                            "detail": "auto"
                        }
                    ]
                }
            ]
        )

        raw = response.output_text.strip()

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

        memories = decision.get("memories", [])

        if not memories:

            print(
                "Nuotraukoje nerasta ilgalaikei "
                "atminciai svarbiu faktu.",
                flush=True
            )

            return

        for item in memories:

            memory_key = (
                item.get("memory_key", "").strip()
            )

            memory = (
                item.get("memory", "").strip()
            )

            category = (
                item.get("category", "travel").strip()
            )

            if not memory_key or not memory:
                continue

            save_long_term_memory(
                chat_id=chat_id,
                memory_key=memory_key,
                category=category,
                memory=memory,
                source_type="image",
                source_message_id=source_message_id
            )

        print(
            f"Nuotraukos atminties analize baigta. "
            f"Rasta faktu: {len(memories)}",
            flush=True
        )

    except Exception as e:

        print(
            f"Nuotraukos atminties analizes klaida: "
            f"{type(e).__name__}: {e}",
            flush=True
        )


# ============================================================
# REPLY Į ROBĄ
# ============================================================

def is_reply_to_roba(message):

    reply = message.get("reply_to_message")

    if not reply:
        return False

    reply_from = reply.get("from", {})

    if (
        BOT_ID
        and reply_from.get("id") == BOT_ID
    ):
        return True

    reply_username = (
        reply_from.get("username", "").lower()
    )

    if (
        BOT_USERNAME
        and reply_username == BOT_USERNAME
    ):
        return True

    return False


def get_reply_context(message):

    reply = message.get("reply_to_message")

    if not reply:
        return ""

    reply_text = (
        reply.get("text")
        or reply.get("caption")
        or ""
    )

    if not reply_text:
        return ""

    reply_from = reply.get("from", {})

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
        # NAUJA NUOTRAUKA
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
                "Nauja nuotrauka isiminta RAM.",
                flush=True
            )

        # ----------------------------------------------------
        # VISKĄ SAUGOM SUPABASE
        # ----------------------------------------------------

        save_message_to_db(
            chat_id=chat_id,
            telegram_message_id=message_id,
            sender_name=name,
            sender_id=sender_id,
            message_text=text,
            has_photo=bool(photo_file_id),
            photo_file_id=photo_file_id
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
        # TEKSTO ILGALAIKĖ ATMINTIS
        # ----------------------------------------------------

        if (
            text
            and should_analyze_for_memory(text)
            and not is_forget_request(text)
        ):

            print(
                "Vietinis filtras: zinute gali buti "
                "svarbi -> kvieciamas atminties AI.",
                flush=True
            )

            memory_thread = threading.Thread(
                target=analyze_message_for_memory,
                args=(
                    chat_id,
                    name,
                    text,
                    message_id
                ),
                daemon=True
            )

            memory_thread.start()

        elif text:

            print(
                "Vietinis filtras: ilgalaikes "
                "teksto atminties AI nekvieciamas.",
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
                f"@{BOT_USERNAME}" in lower_text
            )

        should_answer = (
            called_by_name
            or called_by_username
            or replied_to_roba
        )

        if not should_answer:

            print(
                "Roba nekviestas - atsakymo nebus.",
                flush=True
            )

            return

        # ----------------------------------------------------
        # TIKRAS ILGALAIKĖS ATMINTIES PAMIRŠIMAS
        # ----------------------------------------------------

        if text and is_forget_request(text):

            forget_answer = handle_forget_request(
                chat_id=chat_id,
                text=text
            )

            send_result = send_message(
                chat_id,
                forget_answer,
                message_id
            )

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
                message_text=forget_answer,
                has_photo=False,
                photo_file_id=None
            )

            history[chat_id].append(
                f"Roba: {forget_answer}"
            )

            print(
                "Atminties pamirsimo veiksmas atliktas.",
                flush=True
            )

            return

        # ----------------------------------------------------
        # TODO SĄRAŠO VEIKSMAS
        # ----------------------------------------------------

        todo_answer = None

        if text:
            todo_answer = handle_todo(
                chat_id=chat_id,
                sender_name=name,
                text=text
            )

        if todo_answer:

            send_result = send_message(
                chat_id,
                todo_answer,
                message_id
            )

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
                message_text=todo_answer,
                has_photo=False,
                photo_file_id=None
            )

            history[chat_id].append(
                f"Roba: {todo_answer}"
            )

            print(
                "TODO veiksmas atliktas.",
                flush=True
            )

            return

        # ----------------------------------------------------
        # POKALBIO ISTORIJA
        # ----------------------------------------------------

        db_messages = get_recent_messages_from_db(
            chat_id,
            limit=60
        )

        if db_messages:

            conversation = "\n".join(
                db_messages
            )

        else:

            conversation = "\n".join(
                history[chat_id]
            )

        long_term_memory = get_long_term_memory(
            chat_id
        )

        # ----------------------------------------------------
        # SURANDAM NUOTRAUKĄ
        # ----------------------------------------------------

        image_file_id = None
        image_source_message_id = None

        if photo_file_id:

            image_file_id = photo_file_id
            image_source_message_id = message_id

        elif (
            chat_id in last_photo
            and not photo_used[chat_id]
        ):

            image_file_id = (
                last_photo[chat_id]["file_id"]
            )

            image_source_message_id = (
                last_photo[chat_id]["message_id"]
            )

            print(
                "Naudojama paskutine "
                "neanalizuota RAM nuotrauka.",
                flush=True
            )

        else:

            db_photo = get_last_photo_from_db(
                chat_id
            )

            if db_photo:

                image_file_id = (
                    db_photo.get("photo_file_id")
                )

                image_source_message_id = (
                    db_photo.get(
                        "telegram_message_id"
                    )
                )

                if image_file_id:

                    print(
                        "Paskutine nuotrauka "
                        "rasta Supabase.",
                        flush=True
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
        # PAGRINDINĖ OPENAI UŽKLAUSA
        # ----------------------------------------------------

        prompt_text = (
            "ILGALAIKĖ ROBOS ATMINTIS:\n\n"
            f"{long_term_memory or '(dar nėra)'}\n\n"
            "PASKUTINIS GRUPĖS POKALBIS:\n\n"
            f"{conversation}\n"
            f"{reply_context}\n"
            "Atsakyk į naujausią žmogaus žinutę:\n"
            f"{name}: {text}"
        )

        content = [
            {
                "type": "input_text",
                "text": prompt_text
            }
        ]

        image_data_url = None

        if image_file_id:

            print(
                "Parsiunciama Telegram nuotrauka...",
                flush=True
            )

            image_data_url = get_telegram_photo_base64(
                image_file_id
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
                "pagrindines OpenAI uzklausos.",
                flush=True
            )

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
            ]
        )

        answer = response.output_text.strip()

        if not answer:

            print(
                "OpenAI grazino tuscia atsakyma.",
                flush=True
            )

            return

        # ----------------------------------------------------
        # ATSAKOM TELEGRAM
        # ----------------------------------------------------

        send_result = send_message(
            chat_id,
            answer,
            message_id
        )

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
            has_photo=False,
            photo_file_id=None
        )

        history[chat_id].append(
            f"Roba: {answer}"
        )

        # ----------------------------------------------------
        # JEIGU ROBĄ KVIETĖ PRIE NUOTRAUKOS,
        # ATSKIRAI IŠRENKAM ILGALAIKIUS FAKTUS
        # ----------------------------------------------------

        if image_data_url:

            print(
                "Paleidziama nuotraukos "
                "ilgalaikes atminties analize.",
                flush=True
            )

            image_memory_thread = threading.Thread(
                target=analyze_image_for_memory,
                args=(
                    chat_id,
                    image_data_url,
                    image_source_message_id,
                    text
                ),
                daemon=True
            )

            image_memory_thread.start()

            photo_used[chat_id] = True

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
                f"Nepavyko issiusti klaidos "
                f"zinutes: {send_error}",
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
            f"Update ID: {data.get('update_id')}",
            flush=True
        )

        message = (
            data.get("message")
            or data.get("edited_message")
        )

        if not message:
            return "OK", 200

        user = message.get("from", {})

        if user.get("is_bot"):
            return "OK", 200

        chat = message.get("chat", {})
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

        photos = message.get("photo", [])

        photo_file_id = None

        if photos:

            photo_file_id = (
                photos[-1].get("file_id")
            )

        replied_to_roba = is_reply_to_roba(
            message
        )

        reply_context = get_reply_context(
            message
        )

        if not text and not photo_file_id:
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
