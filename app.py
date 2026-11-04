import os
import json
import base64
import re
import threading
import contextvars
import urllib.request
import urllib.error
import urllib.parse
import tempfile
import subprocess
import shutil

import imageio_ffmpeg
from collections import defaultdict, deque
from pathlib import Path
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

from flask import Flask, request, jsonify
from openai import OpenAI
from supabase import create_client


# ============================================================
# NUSTATYMAI
# ============================================================

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_VYRU_TOKEN = os.environ.get("TELEGRAM_VYRU_TOKEN", "")
VYRU_CHAT_ID = -699814801
_active_bot = contextvars.ContextVar("active_bot", default="main")
_vyru_identity = {}

def current_token():
    return TELEGRAM_VYRU_TOKEN if _active_bot.get() == "vyru" else TELEGRAM_TOKEN

def current_bot_id():
    return _vyru_identity.get("id") if _active_bot.get() == "vyru" else BOT_ID

def current_bot_username():
    return _vyru_identity.get("username") if _active_bot.get() == "vyru" else BOT_USERNAME

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
