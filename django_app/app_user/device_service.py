"""
Qurilmalar (UserDevice) bilan ishlash: login paytida qurilmani ro'yxatga olish,
2 ta faol qurilma cheklovi va o'chirilgan qurilma tokenlarini rad etish.
"""
import hashlib

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from .models import UserDevice

MAX_ACTIVE_DEVICES = 2
# Cheklov faqat shu rollarga qo'llanadi
LIMITED_ROLES = {"student"}
# Tokendagi qurilma identifikatori claim nomi
DEVICE_CLAIM = "did"

_STATUS_CACHE = "udev-active:{}"
_SEEN_CACHE = "udev-seen:{}"
_STATUS_TTL = 60  # soniya: o'chirilgan qurilma ko'pi bilan shu vaqt ichida bloklanadi (o'chirishda kesh darhol tozalanadi)
_SEEN_TTL = 300  # last_used_at ni har so'rovda emas, 5 daqiqada bir yangilaymiz


class DeviceLimitReached(Exception):
    def __init__(self, devices):
        super().__init__("Qurilmalar soni chegarasiga yetildi")
        self.devices = devices


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    ip = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")
    return ip or None


def _parse_user_agent(ua_string):
    """User-Agent dan qurilma nomi va turini aniqlaydi ("Windows 10, Chrome 149")."""
    if not ua_string:
        return "", "other"
    try:
        from user_agents import parse
    except ImportError:  # kutubxona o'rnatilmagan bo'lsa — xom qator
        return ua_string[:120], "other"

    ua = parse(ua_string)
    os_name = " ".join(filter(None, [ua.os.family, ua.os.version_string])).strip()
    browser = " ".join(filter(None, [ua.browser.family, str(ua.browser.version[0]) if ua.browser.version else ""])).strip()
    if ua.is_mobile or ua.is_tablet:
        device = " ".join(filter(None, [ua.device.brand, ua.device.model])).strip()
        name = ", ".join(filter(None, [device or os_name, browser if browser != "Other" else ""]))
    else:
        name = ", ".join(filter(None, [os_name, browser if browser != "Other" else ""]))

    device_type = "tablet" if ua.is_tablet else "mobile" if ua.is_mobile else "desktop" if ua.is_pc else "other"
    return (name or ua_string[:120])[:255], device_type


def device_info_from_request(request):
    """
    Frontend yuboradigan maydonlar (hammasi ixtiyoriy):
      device_id   — brauzer/ilovada saqlangan doimiy UUID
      user_agent  — haqiqiy brauzer User-Agent (next-auth serverdan so'rov yuborgani uchun)
      device_name — tayyor nom (mobil ilova uchun, masalan "Redmi Note 12")
    device_id bo'lmasa, qurilma User-Agent xeshi bo'yicha taniladi.
    """
    data = request.data
    device_id = str(data.get("device_id") or request.headers.get("X-Device-Id") or "").strip()[:64]
    ua_string = str(data.get("user_agent") or request.META.get("HTTP_USER_AGENT") or "")[:1000]
    parsed_name, device_type = _parse_user_agent(ua_string)
    device_name = str(data.get("device_name") or "").strip()[:255] or parsed_name

    if device_id:
        device_key = f"id:{device_id}"
    else:
        device_key = "ua:" + hashlib.sha1(ua_string.encode("utf-8")).hexdigest()

    return {
        "device_key": device_key,
        "device_name": device_name or "Noma'lum qurilma",
        "device_type": device_type,
        "user_agent": ua_string,
        "ip_address": client_ip(request),
    }


def _forget_cache(device_id):
    cache.delete(_STATUS_CACHE.format(device_id))
    cache.delete(_SEEN_CACHE.format(device_id))


def deactivate_device(device):
    if device.is_active:
        device.is_active = False
        device.logged_out_at = timezone.now()
        device.save(update_fields=["is_active", "logged_out_at"])
    _forget_cache(device.id)


def register_login(user, request, replace_device_id=None):
    """
    Login paytida qurilmani ro'yxatga oladi va UserDevice qaytaradi.
    Cheklangan rol uchun faol qurilmalar soni to'lgan bo'lsa DeviceLimitReached ko'tariladi,
    agar replace_device_id berilmagan bo'lsa (u holda o'sha qurilma chiqarib yuboriladi).
    Cheklanmagan rollar uchun None qaytaradi (qurilma yozilmaydi).
    """
    if user.role not in LIMITED_ROLES:
        return None

    info = device_info_from_request(request)
    with transaction.atomic():
        # Bir vaqtdagi ikki login cheklovni aylanib o'tmasligi uchun foydalanuvchi qatorini qulflaymiz
        type(user).objects.select_for_update().filter(pk=user.pk).first()
        active = list(UserDevice.objects.filter(user=user, is_active=True).order_by("-last_used_at"))

        # Shu qurilmadan qayta kirilyapti — yangi joy egallamaydi
        same = next((device for device in active if device.device_key == info["device_key"]), None)
        if same:
            for field in ("device_name", "device_type", "user_agent", "ip_address"):
                setattr(same, field, info[field])
            same.last_used_at = timezone.now()
            same.save()
            _forget_cache(same.id)
            return same

        if len(active) >= MAX_ACTIVE_DEVICES:
            target = next((device for device in active if str(device.id) == str(replace_device_id)), None)
            if not target:
                raise DeviceLimitReached(active)
            deactivate_device(target)

        return UserDevice.objects.create(user=user, **info)


def serialize_device(device, current_id=None):
    return {
        "id": str(device.id),
        "device_name": device.device_name,
        "device_type": device.device_type,
        "ip_address": device.ip_address,
        "is_active": device.is_active,
        "is_current": current_id is not None and str(device.id) == str(current_id),
        "created_at": device.created_at.isoformat() if device.created_at else None,
        "last_used_at": device.last_used_at.isoformat() if device.last_used_at else None,
        "logged_out_at": device.logged_out_at.isoformat() if device.logged_out_at else None,
    }


def device_limit_response_data(devices):
    return {
        "code": "device_limit",
        "detail": f"Siz bir vaqtda ko'pi bilan {MAX_ACTIVE_DEVICES} ta qurilmadan foydalana olasiz. "
                  "Davom etish uchun qurilmalardan birini chiqarib yuboring.",
        "max_devices": MAX_ACTIVE_DEVICES,
        "devices": [serialize_device(device) for device in devices],
    }


def attach_device_claim(refresh, access, device):
    """Qurilma identifikatorini tokenlarga yozadi (refresh orqali olingan access ham meros oladi)."""
    if device is None:
        return
    refresh[DEVICE_CLAIM] = str(device.id)
    access[DEVICE_CLAIM] = str(device.id)


def is_device_active(device_id):
    """Token qurilmasi faolmi (60 soniya keshlanadi); faol bo'lsa last_used_at ni vaqti-vaqti bilan yangilaydi."""
    key = _STATUS_CACHE.format(device_id)
    status = cache.get(key)
    if status is None:
        status = UserDevice.objects.filter(id=device_id, is_active=True).exists()
        cache.set(key, status, _STATUS_TTL)

    if status and not cache.get(_SEEN_CACHE.format(device_id)):
        UserDevice.objects.filter(id=device_id).update(last_used_at=timezone.now())
        cache.set(_SEEN_CACHE.format(device_id), True, _SEEN_TTL)
    return status
