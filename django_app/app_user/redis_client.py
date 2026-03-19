"""
Ro'yxatdan o'tish jarayoni uchun Redis yordamchi moduli.
Celery (db=0) va channels (db=1) ga ta'sir qilmaslik uchun db=2 ishlatiladi.
"""
import json
from typing import Optional
import redis
from django.conf import settings

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = redis.from_url(
            getattr(settings, "REGISTRATION_REDIS_URL", "redis://127.0.0.1:6379/2"),
            decode_responses=True,
        )
    return _client


def _key(phone: str) -> str:
    return f"reg:{phone}"


def save_pending_registration(phone: str, data: dict) -> None:
    """
    Ro'yxatdan o'tish ma'lumotlarini Redisga saqlaydi.
    TTL: REGISTRATION_REDIS_TTL (default 600 soniya = 10 daqiqa).
    """
    ttl = getattr(settings, "REGISTRATION_REDIS_TTL", 600)
    _get_client().setex(_key(phone), ttl, json.dumps(data, ensure_ascii=False))


def get_pending_registration(phone: str) -> Optional[dict]:
    """Redisdan ro'yxatdan o'tish ma'lumotlarini oladi. Topilmasa None qaytaradi."""
    raw = _get_client().get(_key(phone))
    if raw is None:
        return None
    return json.loads(raw)


def delete_pending_registration(phone: str) -> None:
    """Redis kalitini o'chiradi (SMS tasdiqlangandan keyin)."""
    _get_client().delete(_key(phone))
