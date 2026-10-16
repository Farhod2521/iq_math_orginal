"""Telegram Bot API ga oddiy so'rovlar (requests orqali, polling kerak emas)."""
import logging
import time

import requests

from . import config

logger = logging.getLogger(__name__)

MAX_RETRIES = 5


class TelegramError(Exception):
    pass


def _call(method, data=None, files=None, timeout=60):
    if not config.BOT_TOKEN:
        raise TelegramError("TELEGRAM_BOT_TOKEN .telegram-env faylida yozilmagan.")
    url = f"{config.API_URL}/bot{config.BOT_TOKEN}/{method}"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(url, data=data, files=files, timeout=timeout)
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            if attempt == MAX_RETRIES:
                raise TelegramError(f"{method}: {exc}") from exc
            time.sleep(5 * attempt)
            continue

        if payload.get("ok"):
            return payload["result"]
        # Juda ko'p so'rov — Telegram aytgan vaqtcha kutamiz
        retry_after = (payload.get("parameters") or {}).get("retry_after")
        if response.status_code == 429 and retry_after and attempt < MAX_RETRIES:
            time.sleep(int(retry_after) + 1)
            continue
        raise TelegramError(f"{method}: {payload.get('description')}")
    raise TelegramError(f"{method}: urinishlar tugadi")


def send_message(chat_id, text):
    return _call("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    })


def send_document(chat_id, filename, content, caption=""):
    """content — bytes yoki ochiq fayl obyekti"""
    return _call(
        "sendDocument",
        {"chat_id": chat_id, "caption": caption[:1024], "parse_mode": "HTML"},
        files={"document": (filename, content)},
        timeout=600,
    )


def resend_document(chat_id, file_id, caption=""):
    """Bir marta yuklangan faylni boshqa chatga qayta yuklamasdan yuborish"""
    return _call("sendDocument", {
        "chat_id": chat_id,
        "document": file_id,
        "caption": caption[:1024],
        "parse_mode": "HTML",
    })


def broadcast(chat_ids, text):
    """Bir nechta chatga xabar; biri xato bersa qolganlariga baribir yuboriladi."""
    sent = 0
    for chat_id in chat_ids:
        try:
            send_message(chat_id, text)
            sent += 1
        except TelegramError as exc:
            logger.error("Telegram xabar yuborilmadi (%s): %s", chat_id, exc)
    return sent
