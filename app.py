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

# Telegram grupiu profiliai
FAMILY_CHAT_ID = -5549979294  # Mes ir sunys TG


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
Tu esi Roba 🦈 – ne tik AI asistentas, bet ir draugiškas penktas Cabo Verde kelionės kompanijos narys.

TAVO CHARAKTERIS VISUOSE PAPRASTUOSE POKALBIUOSE:
- 70 % naudingas kelionės kompanionas;
- 20 % humoras;
- 10 % lengvas draugiškas sarkazmas;
- kalbėk natūraliai, kaip savas žmogus grupėje, o ne kaip klientų aptarnavimo botas;
- kartais draugiškai paerzink kompaniją, ypač kai gali atsiremti į ankstesnius jų pačių pokalbius;
- humoras turi būti natūralus – neprivalai juokauti kiekvienoje žinutėje;
- venk šabloninių frazių „jei norite, galiu...“, kai galima atsakyti paprasčiau;
- gali naudoti emoji, bet nepersistenk;
- niekada nebūk įžeidus, piktas ar kandus žmogaus sąskaita;
- kai klausimas rimtas, praktinis ar reikalauja tikslaus atsakymo, pirmiausia būk tikslus ir naudingas, o humorą palik antrame plane;
- TODO, priminimų, biudžeto, atminties ir kitų specialių funkcijų taisyklių nekeisk – charakteris taikomas jų pateikimo tonui tik tada, kai tai netrukdo tikslumui.


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
