import os
from pathlib import Path

from dotenv import load_dotenv

BOT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BOT_DIR.parent
STATE_FILE = BOT_DIR / "state.json"

load_dotenv(BOT_DIR / ".telegram-env")


def _ids(name):
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
ADMIN_CHAT_IDS = _ids("TELEGRAM_ADMIN_CHAT_IDS")
MARKETING_CHAT_IDS = _ids("TELEGRAM_MARKETING_CHAT_IDS")
API_URL = os.getenv("TELEGRAM_API_URL", "https://api.telegram.org").rstrip("/")

PART_SIZE = int(float(os.getenv("BACKUP_PART_SIZE_MB", "45")) * 1024 * 1024)
MEDIA_DIRS = _ids("BACKUP_MEDIA_DIRS")
MEDIA_MODE = os.getenv("BACKUP_MEDIA_MODE", "incremental").strip().lower()
TMP_DIR = os.getenv("BACKUP_TMP_DIR", "").strip() or None
PG_DUMP_BIN = os.getenv("PG_DUMP_BIN", "pg_dump").strip() or "pg_dump"
