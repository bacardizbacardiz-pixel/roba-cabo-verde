import os
import json
import base64
import re
import threading
import urllib.request
from collections import defaultdict, deque
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

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

Telegram atsakymuose gali naudoti paprastą Markdown:
- **tekstas** paryškinimui;
- *tekstas* kursyvui;
- ~~tekstas~~ perbraukimui.
Nenaudok sudėtingo Markdown, lentelių ar Markdown antraščių.

SVARBU APIE PRIMINIMUS:
Niekada paprastame pokalbio atsakyme neteigk „priminsiu“, „nustačiau priminimą“
ar panašiai. Tik specialus priminimų modulis gali patvirtinti, kad priminimas
realiai išsaugotas. Jei žmogus kalba apie priminimą, bet specialus modulis jo
nesukūrė, nepateik melagingo patvirtinimo.

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

DATOS IR LAIKAI:
- Niekada nepridėk konkretaus skrydžio, išvykimo ar rezervacijos laiko,
  jeigu jis nėra aiškiai pateiktas atmintyje, pokalbyje, nuotraukoje
  arba patikimame paieškos rezultate.
- Skaičiuodamas „kiek liko iki kelionės“, jei žinai tik kelionės datą,
  pateik dienų skaičių ir datą, bet nesugalvok valandos.
- Jei keli atminties įrašai konfliktuoja, aiškiai pasakyk, kad yra
  neatitikimas, o ne pasirink atsitiktinę reikšmę.



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

Naudok šiuos STABILIUS raktus, kai tema atitinka:
hotel_warsaw
airport_transfer
room_type
flight_outbound
flight_return
travel_dates
traveler_count
meal_plan
travel_insurance
reservation_total_price
excursion_sal
luggage
powerbank

Nekurk naujo rakto su data ar kitu sinonimu, jeigu tinka vienas iš
aukščiau esančių stabilių raktų.
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

Kai tema atitinka, PRIVALOMAI naudok šiuos stabilius raktus:
flight_outbound
flight_return
travel_dates
traveler_count
meal_plan
room_type
travel_insurance
reservation_total_price
hotel_warsaw
airport_transfer
excursion_sal
powerbank

Nekurk datos memory_key pavadinime ir nekurk sinoniminio rakto,
jeigu tinka vienas iš šių raktų.

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
# STABILŪS ILGALAIKĖS ATMINTIES RAKTAI
# ============================================================

MEMORY_KEY_ALIASES = {
    "flight_departure_warsaw_2026-11-30": "flight_outbound",
    "outbound_flight": "flight_outbound",
    "flight_outbound": "flight_outbound",

    "flight_return_sal_2026-12-07": "flight_return",
    "return_flight": "flight_return",
    "flight_return": "flight_return",

    "travel_dates_sal_2026-11-30_2026-12-08": "travel_dates",
    "reservation_dates": "travel_dates",
    "travel_dates": "travel_dates",

    "travel_group_4_adults": "traveler_count",
    "traveler_count": "traveler_count",

    "sal_package_all_inclusive": "meal_plan",
    "meal_plan": "meal_plan",

    "sal_rooms_2_double": "room_type",
    "room_type": "room_type",

    "travel_insurance_sal_2026": "travel_insurance",
    "travel_insurance": "travel_insurance",

    "sal_reservation_total_price": "reservation_total_price",
    "reservation_total_price": "reservation_total_price",

    "powerbankas": "powerbank",
    "powerbank": "powerbank"
}


def canonical_memory_key(memory_key):

    key = (memory_key or "").strip().lower()

    key = re.sub(
        r"[^a-z0-9_]+",
        "_",
        key
    ).strip("_")

    return MEMORY_KEY_ALIASES.get(
        key,
        key
    )

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

        memory_key = canonical_memory_key(
            memory_key
        )

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



def is_possible_todo_request(text, current_items=None):

    normalized = normalize_todo_word(text or "")

    direct_words = [
        "todo",
        "to do",
        "uzduociu saras",
        "darbu saras",
        "itrauk",
        "irasyk",
        "pridek",
        "pasalink",
        "istrink",
        "pazymek atlikta",
        "padaryta",
        "atlikta",
        "jau padarem",
        "jau padariau",
        "jau nupirkom",
        "jau nupirkau"
    ]

    if any(word in normalized for word in direct_words):
        return True

    # Jei žinutėje minimas konkretus atviras TODO punktas ir kartu yra
    # atlikimo / šalinimo veiksmažodis, verta kviesti TODO AI.
    action_words = [
        "jau",
        "padarem",
        "padariau",
        "nupirkom",
        "nupirkau",
        "atlikom",
        "atlikau",
        "istrink",
        "pasalink"
    ]

    if current_items and any(word in normalized for word in action_words):

        for item in current_items:
            task = normalize_todo_word(item.get("task") or "")
            task_words = [
                w for w in task.split()
                if len(w) >= 4
            ]

            if any(w in normalized for w in task_words):
                return True

    return False

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


def is_todo_delete_request(text, current_items):
    lower = normalize_todo_word(text or "")
    delete_words = (
        "pamirsk", "uzmirsk", "istrink", "pasalink",
        "isimk", "isbrauk"
    )
    if not any(word in lower for word in delete_words):
        return False

    # Explicit memory wording must remain a long-term-memory request.
    if "atmint" in lower:
        return False

    # Numbered TODO reference, e.g. "pamiršk 1 punktą".
    if re.search(r"\b\d+\s*(?:punk|nr|numer)", lower):
        return bool(current_items)

    # Or the request contains/matches an actual open TODO item.
    cleaned = lower
    for word in ("roba",) + delete_words:
        cleaned = cleaned.replace(word, " ")
    cleaned = re.sub(r"\b(?:todo|punkta|punkta|punktas|punktą|sarasas|saraso)\b", " ", cleaned)
    cleaned = " ".join(cleaned.split())

    if cleaned and find_best_todo_match(current_items, cleaned):
        return True

    return False


def handle_todo_delete_direct(chat_id, text, current_items):
    lower = normalize_todo_word(text or "")

    # Number refers to the current open TODO list order.
    m = re.search(r"\b(\d+)\s*(?:punk|nr|numer)", lower)
    if m:
        index = int(m.group(1)) - 1
        if index < 0 or index >= len(current_items):
            return (
                f"TODO sąraše dabar yra {len(current_items)} punktai. "
                "Parašyk „Roba, parodyk TODO“ 🙂"
            )
        match = current_items[index]
    else:
        cleaned = lower
        for word in (
            "roba", "pamirsk", "uzmirsk", "istrink",
            "pasalink", "isimk", "isbrauk", "todo"
        ):
            cleaned = cleaned.replace(word, " ")
        cleaned = re.sub(
            r"\b(?:punkta|punktas|punktą|sarasa|sarasas|saraso)\b",
            " ",
            cleaned
        )
        cleaned = " ".join(cleaned.split())
        match = find_best_todo_match(current_items, cleaned)

    if not match:
        return (
            "Neradau tokio punkto dabartiniame TODO sąraše. "
            "Parašyk „Roba, parodyk TODO“ 🙂"
        )

    (
        supabase.table("roba_todo")
        .delete()
        .eq("id", match["id"])
        .eq("chat_id", chat_id)
        .execute()
    )

    return f"Ištryniau iš TODO 🗑️\n{match.get('task')}"


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
# BENDRAS KELIONĖS BIUDŽETAS
# ============================================================

BUDGET_PROMPT = """
Tu esi Robos bendro Cabo Verde kelionės biudžeto tvarkytojas.

Nustatyk veiksmą:
- add: įrašyti išlaidą;
- list: parodyti išlaidas / biudžetą;
- total: suskaičiuoti sumas;
- delete: ištrinti išlaidą;
- none: ne biudžeto valdymas.

ADD atveju ištrauk:
- description: trumpas išlaidos pavadinimas;
- amount: skaičius;
- currency: EUR, PLN, CVE arba kita aiškiai nurodyta valiuta;
- category: viena iš transport, food, hotel, activities, shopping, other;
- paid_by: kas mokėjo, jei aiškiai pasakyta, kitaip null.

NESPĖK valiutos. Jei suma yra, bet valiutos nėra, grąžink
action="add", bet currency=null.

DELETE atveju query turi būti trumpa paieškos frazė.

TOTAL/LIST atveju papildomų laukų nereikia.

Grąžink TIK validų JSON.

Pavyzdžiai:
{"action":"add","description":"Taksi iš oro uosto","amount":48,"currency":"EUR","category":"transport","paid_by":null}
{"action":"add","description":"Pietūs","amount":3200,"currency":"CVE","category":"food","paid_by":null}
{"action":"list"}
{"action":"total"}
{"action":"delete","query":"taksi"}
{"action":"none"}
"""


def is_possible_budget_request(text):

    lower = (text or "").lower()

    keywords = [
        "biudzet", "biudžet", "islaid", "išlaid",
        "kainavo", "sumokej", "sumokėj", "mokej", "mokėj",
        "eur", "€", "pln", "zl", "zł", "cve",
        "eskud", "kiek isleid", "kiek išleid"
    ]

    has_keyword = any(k in lower for k in keywords)

    has_money = bool(
        re.search(
            r"\b\d+(?:[.,]\d+)?\s*"
            r"(?:€|eur|pln|zl|zł|cve)\b",
            lower
        )
    )

    return has_keyword or has_money


def get_budget_items(chat_id):

    result = (
        supabase
        .table("roba_budget")
        .select(
            "id,description,amount,currency,category,"
            "paid_by,created_by,expense_date,created_at"
        )
        .eq("chat_id", chat_id)
        .order("created_at", desc=False)
        .execute()
    )

    return result.data or []


def detect_budget_action(text):

    response = client.responses.create(
        model="gpt-5.6-luna",
        instructions=BUDGET_PROMPT,
        input=text
    )

    raw = response.output_text.strip()

    if raw.startswith("```"):
        raw = raw.replace("```json", "", 1)
        raw = raw.replace("```", "").strip()

    return json.loads(raw)


def normalize_budget_text(text):

    text = normalize_todo_word(text or "")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def find_budget_match(items, query):

    q = normalize_budget_text(query)

    if not q:
        return None

    words = [w for w in q.split() if len(w) >= 3]
    best = None
    best_score = 0

    for item in items:
        desc = normalize_budget_text(
            item.get("description") or ""
        )

        score = 100 if q in desc or desc in q else 0

        for word in words:
            if word in desc:
                score += 10

        if score > best_score:
            best_score = score
            best = item

    return best if best_score > 0 else None


def format_budget(items):

    if not items:
        return "Kelionės biudžetas kol kas tuščias 💰"

    lines = ["Cabo Verde išlaidos 💰"]

    totals = {}

    for i, item in enumerate(items, start=1):
        amount = float(item.get("amount") or 0)
        currency = (item.get("currency") or "").upper()
        description = item.get("description") or "Išlaida"

        totals[currency] = totals.get(currency, 0) + amount

        lines.append(
            f"{i}. {description} — {amount:g} {currency}"
        )

    lines.append("")
    lines.append("Iš viso pagal valiutas:")

    for currency, amount in totals.items():
        lines.append(f"• {amount:g} {currency}")

    return "\n".join(lines)


def is_budget_delete_request(text, items):
    lower = normalize_budget_text(text or "")
    delete_words = (
        "pamirsk", "uzmirsk", "istrink", "pasalink",
        "isimk", "isbrauk"
    )

    if not any(word in lower for word in delete_words):
        return False

    # Explicit memory wording belongs to long-term memory.
    if "atmint" in lower:
        return False

    cleaned = lower
    for word in ("roba", "biudzeto", "biudzetas", "biudzeta") + delete_words:
        cleaned = cleaned.replace(word, " ")
    cleaned = " ".join(cleaned.split())

    if not cleaned:
        return False

    return find_budget_match(items, cleaned) is not None


def handle_budget_delete_direct(chat_id, text, items):
    lower = normalize_budget_text(text or "")

    cleaned = lower
    for word in (
        "roba", "pamirsk", "uzmirsk", "istrink", "pasalink",
        "isimk", "isbrauk", "biudzeto", "biudzetas", "biudzeta"
    ):
        cleaned = cleaned.replace(word, " ")
    cleaned = " ".join(cleaned.split())

    match = find_budget_match(items, cleaned)

    if not match:
        return (
            "Neradau tokios išlaidos biudžete. "
            "Parašyk „Roba, parodyk biudžetą“ 🙂"
        )

    (
        supabase.table("roba_budget")
        .delete()
        .eq("id", match["id"])
        .eq("chat_id", chat_id)
        .execute()
    )

    return (
        "Ištryniau iš biudžeto 🗑️\n"
        f"• {match.get('description')} — "
        f"{float(match.get('amount') or 0):g} "
        f"{match.get('currency')}"
    )


def handle_budget(chat_id, sender_name, text):

    try:
        decision = detect_budget_action(text)
        action = decision.get("action", "none")

        if action == "none":
            return None

        items = get_budget_items(chat_id)

        if action in ("list", "total"):
            return format_budget(items)

        if action == "add":
            description = (
                decision.get("description") or ""
            ).strip()

            amount = decision.get("amount")
            currency = (
                decision.get("currency") or ""
            ).strip().upper()

            category = (
                decision.get("category") or "other"
            ).strip()

            paid_by = decision.get("paid_by")

            if not description or amount is None:
                return "Kokią išlaidą ir kokią sumą įrašyti? 🙂"

            if not currency:
                return (
                    f"Kokia valiuta buvo {amount} už "
                    f"„{description}“? EUR, PLN, CVE ar kita?"
                )

            supabase.table("roba_budget").insert({
                "chat_id": chat_id,
                "description": description,
                "amount": amount,
                "currency": currency,
                "category": category,
                "paid_by": paid_by,
                "created_by": sender_name,
                "expense_date": datetime.now(
                    ZoneInfo("Europe/Vilnius")
                ).date().isoformat()
            }).execute()

            return (
                "Įrašiau į biudžetą 💰\n"
                f"• {description} — {amount} {currency}"
            )

        if action == "delete":
            match = find_budget_match(
                items,
                decision.get("query", "")
            )

            if not match:
                return (
                    "Neradau tokios išlaidos 🙂 "
                    "Parašyk „Roba, parodyk biudžetą“."
                )

            supabase.table(
                "roba_budget"
            ).delete().eq(
                "id", match["id"]
            ).eq(
                "chat_id", chat_id
            ).execute()

            return (
                "Ištryniau iš biudžeto 🗑️\n"
                f"• {match.get('description')} — "
                f"{float(match.get('amount') or 0):g} "
                f"{match.get('currency')}"
            )

        return None

    except Exception as e:
        print(
            f"Biudzeto apdorojimo klaida: "
            f"{type(e).__name__}: {e}",
            flush=True
        )
        return None

# ============================================================
# PRIMINIMAI
# ============================================================


REMINDER_MANAGEMENT_PROMPT = """
Tu esi Robos Telegram priminimų tvarkytojas.

Nustatyk, ar žmogus:
- nori pamatyti aktyvius priminimus -> "list"
- nori atšaukti / ištrinti priminimą -> "cancel"
- nieko iš šių veiksmų -> "none"

Jeigu veiksmas "cancel", iš žmogaus žinutės ištrauk trumpą paieškos frazę,
pagal kurią galima surasti priminimą, pvz.:
"Roba, atšauk priminimą apie check-in" -> "check-in"

Grąžink TIK validų JSON.

Pavyzdžiai:
{"action":"list","query":""}
{"action":"cancel","query":"check-in"}
{"action":"none","query":""}
"""


def get_pending_reminders(chat_id):

    result = (
        supabase
        .table("roba_reminders")
        .select(
            "id,reminder_text,remind_at,status,created_by"
        )
        .eq("chat_id", chat_id)
        .eq("status", "pending")
        .order("remind_at", desc=False)
        .execute()
    )

    return result.data or []


def format_reminder_list(rows):

    if not rows:
        return "Aktyvių priminimų nėra ⏰"

    lines = ["Mūsų aktyvūs priminimai ⏰"]

    for i, row in enumerate(rows, start=1):

        raw_time = row.get("remind_at")
        text = row.get("reminder_text") or "Priminimas"

        try:
            dt = datetime.fromisoformat(
                raw_time.replace("Z", "+00:00")
            )
            local_dt = dt.astimezone(
                ZoneInfo("Europe/Vilnius")
            )
            pretty = local_dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            pretty = raw_time or "laikas nežinomas"

        lines.append(
            f"{i}. ⏰ {pretty} — {text}"
        )

    return "\n".join(lines)


def normalize_reminder_match_text(text):

    text = (text or "").lower().strip()

    replacements = {
        "ą": "a",
        "č": "c",
        "ę": "e",
        "ė": "e",
        "į": "i",
        "š": "s",
        "ų": "u",
        "ū": "u",
        "ž": "z"
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def find_best_reminder_match(rows, query):

    if not rows:
        return None

    q = normalize_reminder_match_text(query)

    if not q:
        return None

    q_words = [
        word for word in q.split()
        if len(word) >= 3
    ]

    best = None
    best_score = 0

    for row in rows:

        task = normalize_reminder_match_text(
            row.get("reminder_text") or ""
        )

        score = 0

        if q in task or task in q:
            score += 100

        for word in q_words:
            if word in task:
                score += 10

        if score > best_score:
            best_score = score
            best = row

    if best_score <= 0:
        return None

    return best


def detect_reminder_management(text):

    try:
        response = client.responses.create(
            model="gpt-5.6-luna",
            instructions=REMINDER_MANAGEMENT_PROMPT,
            input=text
        )

        raw = response.output_text.strip()

        if raw.startswith("```"):
            raw = raw.replace("```json", "", 1)
            raw = raw.replace("```", "").strip()

        data = json.loads(raw)

        return {
            "action": data.get("action", "none"),
            "query": data.get("query", "")
        }

    except Exception as e:

        print(
            f"Priminimu valdymo atpazinimo klaida: "
            f"{type(e).__name__}: {e}",
            flush=True
        )

        return {
            "action": "none",
            "query": ""
        }


def handle_reminder_management(chat_id, text):

    decision = detect_reminder_management(text)
    action = decision.get("action")

    if action == "list":

        rows = get_pending_reminders(chat_id)
        return format_reminder_list(rows)

    if action == "cancel":

        rows = get_pending_reminders(chat_id)

        if not rows:
            return "Aktyvių priminimų nėra ⏰"

        match = find_best_reminder_match(
            rows,
            decision.get("query", "")
        )

        if not match:
            return (
                "Neradau tokio aktyvaus priminimo 🙂\n"
                "Parašyk „Roba, parodyk priminimus“ "
                "ir pamatysim sąrašą."
            )

        reminder_id = match.get("id")
        reminder_text = match.get("reminder_text") or "Priminimas"

        (
            supabase
            .table("roba_reminders")
            .update({
                "status": "cancelled"
            })
            .eq("id", reminder_id)
            .eq("status", "pending")
            .execute()
        )

        return (
            "Priminimą atšaukiau ✅\n"
            f"📌 {reminder_text}"
        )

    return None

REMINDER_PROMPT = """
Tu esi Robos kelionės priminimų tvarkytojas.

Žmogus prašo sukurti priminimą Telegram grupėje.
Tau pateikiamas dabartinis Lietuvos laikas, ilgalaikė kelionės
atmintis ir žmogaus žinutė.

Nustatyk:
1. ką reikės priminti;
2. tikslų priminimo laiką Europe/Vilnius laiko juostoje.

Suprask natūralias frazes, pvz.:
- primink rytoj 10 val.;
- primink lapkričio 25 d.;
- primink lapkričio 25 d. 18:30;
- primink likus 3 dienoms iki skrydžio.

Jeigu žmogus nurodo datą, bet NENURODO valandos,
naudok 09:00 Europe/Vilnius.

Jeigu žmogus nurodo tik dienos dalį:
- ryte -> 09:00
- per pietus -> 12:00
- vakare -> 19:00

Jeigu laiko ar datos negalima patikimai nustatyti iš žinutės
ir pateiktos atminties, nekurk datos iš spėjimo.

Grąžink TIK validų JSON.

Jeigu galima sukurti:
{
  "save": true,
  "reminder_text": "Padaryti online check-in",
  "remind_at": "2026-11-25T09:00:00+02:00"
}

Jeigu trūksta datos / laiko:
{
  "save": false,
  "question": "Kada tau tai priminti?"
}
"""


def is_reminder_request(text):

    lower = (text or "").lower()

    words = [
        "primink",
        "priminimą",
        "priminima",
        "priminimas",
        "priminimai",
        "priminimus",
        "priminimu"
    ]

    return any(word in lower for word in words)


def save_reminder(
    chat_id,
    reminder_text,
    remind_at,
    created_by,
    source_message_id
):

    result = (
        supabase
        .table("roba_reminders")
        .insert({
            "chat_id": chat_id,
            "reminder_text": reminder_text,
            "remind_at": remind_at,
            "status": "pending",
            "created_by": created_by,
            "source_message_id": source_message_id
        })
        .execute()
    )

    return result.data or []


def get_reminder_followup_text(text, replied_to_roba, reply_context):
    """
    Jei žmogus atsako į Robos klausimą apie priminimo laiką, sujungiame
    ankstesnį priminimo kontekstą su nauju laiko atsakymu.
    Pvz. Roba: "Kada priminti?" -> žmogus: "po 1 minutės".
    """
    if not replied_to_roba:
        return None

    current = (text or "").strip()
    context = (reply_context or "").strip()

    if not current or not context:
        return None

    context_lower = context.lower()

    reminder_context_words = (
        "kada", "priminti", "primin", "laik", "dat"
    )

    if not (
        ("prim" in context_lower)
        and any(word in context_lower for word in reminder_context_words)
    ):
        return None

    # Naujas atsakymas turi atrodyti kaip laikas / data / santykinis laikas.
    current_lower = current.lower()
    time_like = bool(
        re.search(r"\b\d{1,2}(?::\d{2})?\b", current_lower)
        or any(word in current_lower for word in (
            "po ", "minut", "valand", "rytoj", "poryt",
            "šiandien", "siandien", "vakare", "ryte",
            "dien", "savait"
        ))
    )

    if not time_like:
        return None

    return (
        "Tai yra tęsinys ankstesnio priminimo dialogo.\n"
        "ROBOS ANKSTESNĖ ŽINUTĖ:\n"
        f"{context}\n\n"
        "ŽMOGAUS ATSAKYMAS APIE LAIKĄ:\n"
        f"{current}\n\n"
        "Sukurk realų priminimą pagal šį tęstinį dialogą."
    )


def handle_reminder_request(
    chat_id,
    sender_name,
    text,
    message_id
):

    try:
        vilnius_now = datetime.now(
            ZoneInfo("Europe/Vilnius")
        )

        current_memory = get_long_term_memory(chat_id)

        prompt = (
            "DABARTINIS LIETUVOS LAIKAS:\n"
            f"{vilnius_now.isoformat()}\n\n"
            "ILGALAIKĖ KELIONĖS ATMINTIS:\n"
            f"{current_memory or '(tuščia)'}\n\n"
            "ŽMOGAUS ŽINUTĖ:\n"
            f"{text}"
        )

        response = client.responses.create(
            model="gpt-5.6-luna",
            instructions=REMINDER_PROMPT,
            input=prompt
        )

        raw = response.output_text.strip()

        if raw.startswith("```"):
            raw = raw.replace("```json", "", 1)
            raw = raw.replace("```", "").strip()

        decision = json.loads(raw)

        if not decision.get("save"):
            return (
                decision.get("question")
                or "Kada tau tai priminti? 🙂"
            )

        reminder_text = (
            decision.get("reminder_text") or ""
        ).strip()

        remind_at = (
            decision.get("remind_at") or ""
        ).strip()

        if not reminder_text or not remind_at:
            return "Kada ir ką tiksliai priminti? 🙂"

        # Patikriname, kad AI grąžino tikrą ISO datą.
        parsed = datetime.fromisoformat(remind_at)

        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=ZoneInfo("Europe/Vilnius")
            )

        if parsed <= vilnius_now:
            return (
                "Šitas priminimo laikas jau praėjęs 🙂 "
                "Parašyk naują laiką."
            )

        normalized_time = parsed.isoformat()

        save_reminder(
            chat_id=chat_id,
            reminder_text=reminder_text,
            remind_at=normalized_time,
            created_by=sender_name,
            source_message_id=message_id
        )

        pretty_time = parsed.astimezone(
            ZoneInfo("Europe/Vilnius")
        ).strftime("%Y-%m-%d %H:%M")

        return (
            "Priminimą išsaugojau ⏰\n"
            f"📌 {reminder_text}\n"
            f"🕒 {pretty_time}"
        )

    except Exception as e:
        print(
            f"Priminimo apdorojimo klaida: "
            f"{type(e).__name__}: {e}",
            flush=True
        )

        return (
            "Nepavyko tiksliai sukurti priminimo 😅 "
            "Pabandyk parašyti datą ir laiką aiškiau."
        )

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
        "text": text,
        "parse_mode": "Markdown"
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

        # Teksto ilgalaikės atminties analizę paleidžiame vėliau,
        # tik tada, kai paaiškėja, kad žinutė nėra TODO komanda.
        memory_analysis_needed = (
            text
            and should_analyze_for_memory(text)
            and not is_forget_request(text)
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
        # TODO TRYNIMAS TURI PRIORITETĄ PRIEŠ ATMINTIES "PAMIRŠK"
        # ----------------------------------------------------

        if text:

            open_todo_items = get_todo_items(
                chat_id,
                "open"
            )

            if is_todo_delete_request(
                text,
                open_todo_items
            ):

                todo_delete_answer = handle_todo_delete_direct(
                    chat_id=chat_id,
                    text=text,
                    current_items=open_todo_items
                )

                send_result = send_message(
                    chat_id,
                    todo_delete_answer,
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
                    message_text=todo_delete_answer,
                    has_photo=False,
                    photo_file_id=None
                )

                history[chat_id].append(
                    f"Roba: {todo_delete_answer}"
                )

                print(
                    "TODO punktas istrintas tiesiogiai. "
                    "Atminties pamirsimas nekvieciamas.",
                    flush=True
                )

                return

        # ----------------------------------------------------
        # BIUDŽETO TRYNIMAS TURI PRIORITETĄ PRIEŠ ATMINTIES "PAMIRŠK"
        # ----------------------------------------------------

        if text:

            budget_items = get_budget_items(chat_id)

            if is_budget_delete_request(
                text,
                budget_items
            ):

                budget_delete_answer = handle_budget_delete_direct(
                    chat_id=chat_id,
                    text=text,
                    items=budget_items
                )

                send_result = send_message(
                    chat_id,
                    budget_delete_answer,
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
                    message_text=budget_delete_answer,
                    has_photo=False,
                    photo_file_id=None
                )

                history[chat_id].append(
                    f"Roba: {budget_delete_answer}"
                )

                print(
                    "Biudzeto irasas istrintas tiesiogiai. "
                    "Atminties pamirsimas nekvieciamas.",
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
        # PRIMINIMO SUKŪRIMAS / TĘSTINIS DIALOGAS
        # ----------------------------------------------------

        reminder_followup_text = get_reminder_followup_text(
            text=text,
            replied_to_roba=replied_to_roba,
            reply_context=reply_context
        )

        if text and (
            is_reminder_request(text)
            or reminder_followup_text
        ):

            reminder_answer = None

            # Valdymą (parodyk / atšauk) tikriname tik tiesioginei komandai.
            if is_reminder_request(text):
                reminder_answer = handle_reminder_management(
                    chat_id=chat_id,
                    text=text
                )

            if reminder_answer is None:
                reminder_answer = handle_reminder_request(
                    chat_id=chat_id,
                    sender_name=name,
                    text=reminder_followup_text or text,
                    message_id=message_id
                )

            send_result = send_message(
                chat_id,
                reminder_answer,
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
                message_text=reminder_answer,
                has_photo=False,
                photo_file_id=None
            )

            history[chat_id].append(
                f"Roba: {reminder_answer}"
            )

            print(
                "Priminimo veiksmas atliktas. "
                "I ilgalaike atminti nededama.",
                flush=True
            )

            return

        # ----------------------------------------------------
        # BIUDŽETO VEIKSMAS
        # ----------------------------------------------------

        if text and is_possible_budget_request(text):

            print(
                "Biudzeto vietinis filtras: "
                "galimas biudzeto veiksmas -> kvieciamas AI.",
                flush=True
            )

            budget_answer = handle_budget(
                chat_id=chat_id,
                sender_name=name,
                text=text
            )

            if budget_answer:

                send_result = send_message(
                    chat_id,
                    budget_answer,
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
                    message_text=budget_answer,
                    has_photo=False,
                    photo_file_id=None
                )

                history[chat_id].append(
                    f"Roba: {budget_answer}"
                )

                print(
                    "Biudzeto veiksmas atliktas. "
                    "I ilgalaike atminti nededama.",
                    flush=True
                )

                return

        # ----------------------------------------------------
        # TODO SĄRAŠO VEIKSMAS
        # ----------------------------------------------------

        todo_answer = None

        if text:

            open_todo_items = get_todo_items(
                chat_id,
                "open"
            )

            if is_possible_todo_request(
                text,
                open_todo_items
            ):

                print(
                    "TODO vietinis filtras: "
                    "galimas TODO veiksmas -> kvieciamas AI.",
                    flush=True
                )

                todo_answer = handle_todo(
                    chat_id=chat_id,
                    sender_name=name,
                    text=text
                )

            else:

                print(
                    "TODO vietinis filtras: "
                    "AI nekvieciamas.",
                    flush=True
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
                "TODO veiksmas atliktas. "
                "I ilgalaike atminti nededama.",
                flush=True
            )

            return

        # ----------------------------------------------------
        # TEKSTO ILGALAIKĖ ATMINTIS
        # ----------------------------------------------------

        if memory_analysis_needed:

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

            # Saugumo / kainos optimizacija:
            # po Render restarto automatiškai NEIMAME paskutinės senos
            # nuotraukos iš Supabase. Taip nesusiejame nesusijusios
            # naujos žinutės su senu screenshotu ir nekuriame dublikatų.
            print(
                "Naujos neanalizuotos nuotraukos nera - "
                "senas Supabase vaizdas nepridedamas.",
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
# PRIMINIMŲ IŠSIUNTIMAS
# ============================================================

def send_due_reminders():

    now_utc = datetime.now(ZoneInfo("UTC"))
    cutoff = (now_utc + timedelta(minutes=2)).isoformat()

    result = (
        supabase
        .table("roba_reminders")
        .select(
            "id,chat_id,reminder_text,remind_at,status"
        )
        .eq("status", "pending")
        .lte("remind_at", cutoff)
        .order("remind_at", desc=False)
        .limit(50)
        .execute()
    )

    rows = result.data or []
    sent = 0
    failed = 0

    for row in rows:

        reminder_id = row.get("id")
        chat_id = row.get("chat_id")
        reminder_text = row.get("reminder_text") or "Priminimas"

        try:
            message = (
                "⏰ Robos priminimas\n\n"
                f"📌 {reminder_text}"
            )

            send_result = send_message(
                chat_id,
                message
            )

            sent_message_id = (
                send_result
                .get("result", {})
                .get("message_id")
            )

            (
                supabase
                .table("roba_reminders")
                .update({
                    "status": "sent",
                    "sent_at": now_utc.isoformat()
                })
                .eq("id", reminder_id)
                .eq("status", "pending")
                .execute()
            )

            save_message_to_db(
                chat_id=chat_id,
                telegram_message_id=sent_message_id,
                sender_name="Roba",
                sender_id=BOT_ID,
                message_text=message,
                has_photo=False,
                photo_file_id=None
            )

            history[chat_id].append(
                f"Roba: {message}"
            )

            sent += 1

            print(
                f"Priminimas issiustas: ID={reminder_id}",
                flush=True
            )

        except Exception as e:

            failed += 1

            print(
                f"Priminimo ID={reminder_id} "
                f"siuntimo klaida: {type(e).__name__}: {e}",
                flush=True
            )

    return {
        "checked": len(rows),
        "sent": sent,
        "failed": failed
    }


# ============================================================
# PROAKTYVUS + SOCIALUS ROBA
# ============================================================

PROACTIVE_CHECK_HOUR = 9
SOCIAL_CHECK_HOUR = 18
SOCIAL_WEEKDAYS = set(range(7))  # kasdien
PROACTIVE_TRIP_DATE = date(2026, 11, 30)

SOCIAL_PROMPT = """
Tu esi Roba 🦈 – draugiškas penktas Cabo Verde kelionės kompanijos narys
privačioje draugų Telegram grupėje.

Tau pateikiama kelionės atmintis, TODO ir paskutinis grupės pokalbis.
Nuspręsk, ar verta DABAR pačiam pradėti trumpą socialų pokalbį.

Tavo charakteris:
- 70 % naudingas kelionės kompanionas;
- 20 % humoras;
- 10 % lengvas draugiškas sarkazmas;
- skambėk kaip penktas kompanijos narys, o ne klientų aptarnavimo botas;
- kartais draugiškai paerzink kompaniją remdamasis tuo, ką jie patys anksčiau aptarinėjo;
- humoras turi būti natūralus: nebandyk juokauti kiekviename sakinyje;
- gali vartoti kelias tinkamas emoji, bet nepersistenk;
- niekada nebūk įžeidus, piktas ar kandus žmogaus sąskaita.

Taisyklės:
- nerašyk formalios suvestinės;
- būk natūralus ir trumpas;
- venk tipiškų asistento frazių, pvz. „jei norite, galiu padėti“;
- geriausia – vienas konkretus klausimas, pastebėjimas ar lengvas bajeris kompanijai;
- remkis tikru grupės kontekstu ir ilgalaike atmintimi;
- gali su humoru priminti seniau ilgai svarstytą temą;
- nekartok ką tik aptartos temos tuo pačiu kampu;
- jei grupė aktyviai kalbasi, prisitaikyk prie temos;
- gali pats užvesti kalbą apie restoraną, ekskursiją, transferį, viešbutį, barą, paplūdimį, planą ar kitą kelionės temą;
- kasdien sugalvok bent vieną trumpą, natūralią ir su kelione susijusią žinutę ar klausimą;
- nekurk neegzistuojančių faktų, rezervacijų, kainų ar susitarimų;
- grąžink TIK validų JSON.

{"send":true,"message":"🦈 ..."}
"""

def get_proactive_chat_ids():
    ids = set()
    for table in ("roba_messages", "roba_memory", "roba_todo", "roba_reminders", "roba_budget"):
        try:
            result = supabase.table(table).select("chat_id").limit(500).execute()
            for row in (result.data or []):
                if row.get("chat_id") is not None:
                    ids.add(row["chat_id"])
        except Exception as e:
            print(f"Proaktyvaus chat_id paieskos klaida ({table}): {e}", flush=True)
    return list(ids)

def get_proactive_state(chat_id):
    result = (
        supabase.table("roba_proactive")
        .select("chat_id,last_check_at,last_message_at,last_message_type")
        .eq("chat_id", chat_id).limit(1).execute()
    )
    rows = result.data or []
    return rows[0] if rows else None

def save_proactive_state(chat_id, last_check_at=None, last_message_at=None, last_message_type=None):
    existing = get_proactive_state(chat_id)
    payload = {"chat_id": chat_id, "updated_at": datetime.now(ZoneInfo("UTC")).isoformat()}
    if last_check_at is not None:
        payload["last_check_at"] = last_check_at
    if last_message_at is not None:
        payload["last_message_at"] = last_message_at
    if last_message_type is not None:
        payload["last_message_type"] = last_message_type
    if existing:
        supabase.table("roba_proactive").update(payload).eq("chat_id", chat_id).execute()
    else:
        supabase.table("roba_proactive").insert(payload).execute()

def _parse_iso_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None

def get_open_todo_for_proactive(chat_id):
    try:
        result = (
            supabase.table("roba_todo").select("task")
            .eq("chat_id", chat_id).eq("status", "open")
            .order("created_at", desc=False).limit(10).execute()
        )
        return [r.get("task") for r in (result.data or []) if r.get("task")]
    except Exception:
        return []

def get_pending_reminders_for_proactive(chat_id):
    try:
        result = (
            supabase.table("roba_reminders").select("reminder_text,remind_at")
            .eq("chat_id", chat_id).eq("status", "pending")
            .order("remind_at", desc=False).limit(5).execute()
        )
        return result.data or []
    except Exception:
        return []

def build_proactive_message(chat_id, now_local):
    days = (PROACTIVE_TRIP_DATE - now_local.date()).days
    todo = get_open_todo_for_proactive(chat_id)
    reminders = get_pending_reminders_for_proactive(chat_id)

    milestones = {60, 30, 14, 7, 3, 1}
    if days in milestones:
        lines = [f"🦈 Iki Cabo Verde kelionės liko **{days} d.**"]
        if todo:
            lines += ["", f"📋 TODO dar liko: **{len(todo)}**"]
            lines += [f"• {task}" for task in todo[:5]]
        if reminders:
            lines += ["", "⏰ Artimiausi suplanuoti priminimai:"]
            for row in reminders[:3]:
                when = _parse_iso_datetime(row.get("remind_at"))
                when_text = (
                    when.astimezone(ZoneInfo("Europe/Vilnius")).strftime("%Y-%m-%d %H:%M")
                    if when else "laikas nenurodytas"
                )
                lines.append(f"• {when_text} — {row.get('reminder_text')}")
        return "\n".join(lines), "trip_countdown"

    if days == 0:
        return (
            "🦈✈️ **Šiandien išskrendam į Cabo Verde!**\n\n"
            "Pagal išsaugotą rezervaciją skrydis iš WAW numatytas **05:55**. "
            "Geros kelionės! 🌴",
            "departure_day"
        )
    return None, None

def build_social_message(chat_id, now_local):
    days = (PROACTIVE_TRIP_DATE - now_local.date()).days
    memory = get_long_term_memory(chat_id)
    recent = get_recent_messages_from_db(chat_id, limit=25)
    todo = get_open_todo_for_proactive(chat_id)

    prompt = (
        f"IKI KELIONĖS LIKO DIENŲ: {days}\n\n"
        f"ILGALAIKĖ ATMINTIS:\n{memory or '(tuščia)'}\n\n"
        "NEATLIKTI TODO:\n"
        f"{chr(10).join('- ' + x for x in todo) if todo else '(nėra)'}\n\n"
        "PASKUTINIS GRUPĖS POKALBIS:\n"
        f"{chr(10).join(recent) if recent else '(nėra)'}"
    )

    response = client.responses.create(
        model="gpt-5.6-luna",
        instructions=SOCIAL_PROMPT,
        input=prompt
    )
    raw = response.output_text.strip()
    if raw.startswith("```"):
        raw = raw.replace("```json", "", 1).replace("```", "").strip()
    decision = json.loads(raw)
    if not decision.get("send"):
        return None
    return (decision.get("message") or "").strip() or None

def check_proactive():
    now_local = datetime.now(ZoneInfo("Europe/Vilnius"))
    now_utc = datetime.now(ZoneInfo("UTC"))
    checked = 0
    sent = 0

    # Kelionės suvestinės – 09:00.
    if now_local.hour == PROACTIVE_CHECK_HOUR:
        for chat_id in get_proactive_chat_ids():
            try:
                state = get_proactive_state(chat_id)
                last_check = _parse_iso_datetime((state or {}).get("last_check_at"))
                if last_check and last_check.astimezone(ZoneInfo("Europe/Vilnius")).date() == now_local.date():
                    continue
                checked += 1
                save_proactive_state(chat_id, last_check_at=now_utc.isoformat())
                message, message_type = build_proactive_message(chat_id, now_local)
                if not message:
                    continue
                send_result = send_message(chat_id, message)
                sent_message_id = send_result.get("result", {}).get("message_id")
                save_message_to_db(chat_id, sent_message_id, "Roba", BOT_ID, message, False, None)
                history[chat_id].append(f"Roba: {message}")
                save_proactive_state(chat_id, last_message_at=now_utc.isoformat(), last_message_type=message_type)
                sent += 1
            except Exception as e:
                print(f"Proaktyvaus Robos klaida chat={chat_id}: {type(e).__name__}: {e}", flush=True)

    # Socialinis pokalbis – kasdien 18:00.
    if now_local.hour == SOCIAL_CHECK_HOUR and now_local.weekday() in SOCIAL_WEEKDAYS:
        for chat_id in get_proactive_chat_ids():
            try:
                state = get_proactive_state(chat_id)
                last_message = _parse_iso_datetime((state or {}).get("last_message_at"))

                if (
                    last_message
                    and last_message.astimezone(ZoneInfo("Europe/Vilnius")).date() == now_local.date()
                    and (state or {}).get("last_message_type") in ("social", "social_silent")
                ):
                    continue

                checked += 1
                message = build_social_message(chat_id, now_local)
                if not message:
                    print(f"Socialus Roba nusprende patyleti: chat={chat_id}", flush=True)
                    # Kad cron nekviestų AI dar 59 kartus tą pačią valandą,
                    # pažymime socialinį patikrinimą kaip atliktą.
                    save_proactive_state(
                        chat_id,
                        last_message_at=now_utc.isoformat(),
                        last_message_type="social_silent"
                    )
                    continue

                send_result = send_message(chat_id, message)
                sent_message_id = send_result.get("result", {}).get("message_id")
                save_message_to_db(chat_id, sent_message_id, "Roba", BOT_ID, message, False, None)
                history[chat_id].append(f"Roba: {message}")
                save_proactive_state(
                    chat_id,
                    last_message_at=now_utc.isoformat(),
                    last_message_type="social"
                )
                sent += 1
                print(f"Socialus Roba pats pradejo pokalbi: chat={chat_id}", flush=True)
            except Exception as e:
                print(f"Socialaus Robos klaida chat={chat_id}: {type(e).__name__}: {e}", flush=True)

    return {"proactive_checked": checked, "proactive_sent": sent}

# ============================================================
# WEB
# ============================================================

@web.route("/")
def home():

    return "Roba Cabo Verde veikia 🦈"


@web.route("/health")
def health():

    return "OK"


@web.route("/check-reminders")
def check_reminders():

    try:
        get_bot_identity()
        result = send_due_reminders()
        proactive_result = check_proactive()

        return jsonify({
            "status": "OK",
            **result,
            **proactive_result
        })

    except Exception as e:

        print(
            f"Priminimu patikrinimo klaida: "
            f"{type(e).__name__}: {e}",
            flush=True
        )

        return jsonify({
            "status": "ERROR",
            "error": str(e)
        }), 500


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
