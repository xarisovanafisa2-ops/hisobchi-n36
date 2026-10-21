import os
import sys
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Agar token .env da bo'lmasa, ogohlantirish
if not BOT_TOKEN:
    print("OGOHLANTIRISH: BOT_TOKEN topilmadi! Iltimos, .env faylida BOT_TOKEN ni belgilang.")
