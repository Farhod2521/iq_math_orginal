"""
Sayt statistikasi uchun yordamchi funksiyalar: tashrif manbasini aniqlash,
viloyat nomlarini yagona kalitga keltirish va IP bo'yicha davlat/viloyatni topish.
"""
import ipaddress
import logging
import os
import re
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Viloyat kalitlari (frontenddagi xarita ham shu kalitlardan foydalanadi)
REGION_NAMES = {
    "toshkent_sh": "Toshkent shahri",
    "toshkent_v": "Toshkent viloyati",
    "andijon": "Andijon",
    "buxoro": "Buxoro",
    "fargona": "Farg'ona",
    "jizzax": "Jizzax",
    "xorazm": "Xorazm",
    "namangan": "Namangan",
    "navoiy": "Navoiy",
    "qashqadaryo": "Qashqadaryo",
    "qoraqalpogiston": "Qoraqalpog'iston",
    "samarqand": "Samarqand",
    "sirdaryo": "Sirdaryo",
    "surxondaryo": "Surxondaryo",
}

# ISO 3166-2:UZ viloyat kodlari (ip-api `region` maydoni shu kodni qaytaradi)
REGION_ISO = {
    "TK": "toshkent_sh", "TO": "toshkent_v", "AN": "andijon", "BU": "buxoro",
    "FA": "fargona", "JI": "jizzax", "XO": "xorazm", "NG": "namangan",
    "NW": "navoiy", "QA": "qashqadaryo", "QR": "qoraqalpogiston", "SA": "samarqand",
    "SI": "sirdaryo", "SU": "surxondaryo",
}

_REGION_PATTERNS = [
    ("qoraqalpogiston", ("qoraqalpo", "karakalpak", "qaraqalpa")),
    ("andijon", ("andij",)),
    ("buxoro", ("buxor", "bukhar")),
    ("jizzax", ("jizza", "jizak", "djizak")),
    ("qashqadaryo", ("qashqa", "kashkad", "qashqad")),
    ("navoiy", ("navoi", "navoiy")),
    ("namangan", ("namang",)),
    ("samarqand", ("samarq", "samark")),
    ("surxondaryo", ("surx", "surkh")),
    ("sirdaryo", ("sird", "syrd")),
    ("fargona", ("farg", "ferg")),
    ("xorazm", ("xorazm", "xorezm", "khorez", "khwarez")),
]

# "google." — domen boshi (google.com, google.co.uz); "t.me" — aniq domen yoki uning subdomeni
SEARCH_HOSTS = ("google.", "yandex.", "bing.", "duckduckgo.", "yahoo.", "baidu.", "ecosia.")
SOCIAL_HOSTS = (
    "facebook.", "instagram.", "youtube.", "tiktok.", "twitter.", "linkedin.", "pinterest.", "threads.",
    "fb.com", "youtu.be", "vk.com", "x.com", "t.co", "ok.ru",
)
TELEGRAM_HOSTS = ("telegram.", "t.me")

GEO_CACHE_KEY = "sitegeo:{}"
GEO_CACHE_TTL = 60 * 60 * 24 * 7


def normalize_region(value):
    """'Toshkent shahri', 'Samarqand viloyati', 'Tashkent Region' ... -> yagona kalit."""
    if not value:
        return ""
    text = re.sub(r"[‘’ʻʼ'`]", "", str(value).lower()).strip()
    if text.upper() in REGION_ISO:
        return REGION_ISO[text.upper()]
    if "toshkent" in text or "tashkent" in text:
        if any(w in text for w in ("vil", "region", "oblast", "province")):
            return "toshkent_v"
        return "toshkent_sh"
    for key, needles in _REGION_PATTERNS:
        if any(n in text for n in needles):
            return key
    return ""


def _host_matches(host, patterns):
    for p in patterns:
        if p.endswith("."):
            if host.startswith(p) or f".{p}" in host:
                return True
        elif host == p or host.endswith(f".{p}"):
            return True
    return False


def detect_source(referrer, utm_source, site_host=""):
    """Tashrif qayerdan kelganini aniqlaydi: direct/search/social/telegram/referral."""
    utm = (utm_source or "").lower().strip()
    if utm:
        if utm in ("tg", "telegram") or "telegram" in utm:
            return "telegram"
        if any(p.strip(".") in utm for p in SEARCH_HOSTS):
            return "search"
        if utm in ("ig", "fb", "yt") or any(p.split(".")[0] in utm for p in SOCIAL_HOSTS if len(p) > 5):
            return "social"

    if not referrer:
        return "direct"
    host = (urlparse(referrer).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if not host or (site_host and (host == site_host or host.endswith(f".{site_host}"))):
        return "direct"
    if _host_matches(host, TELEGRAM_HOSTS):
        return "telegram"
    if _host_matches(host, SEARCH_HOSTS):
        return "search"
    if _host_matches(host, SOCIAL_HOSTS):
        return "social"
    return "referral"


def is_public_ip(ip):
    try:
        addr = ipaddress.ip_address(ip)
    except (TypeError, ValueError):
        return False
    return addr.is_global


def cached_geo(ip):
    if not ip:
        return None
    return cache.get(GEO_CACHE_KEY.format(ip))


def _lookup_maxmind(ips):
    """settings.GEOIP_CITY_DB (GeoLite2-City.mmdb) bo'lsa — lokal bazadan aniqlaydi."""
    db_path = getattr(settings, "GEOIP_CITY_DB", "")
    if not db_path or not os.path.exists(db_path):
        return None
    try:
        import geoip2.database
        import geoip2.errors
    except ImportError:
        return None

    result = {}
    with geoip2.database.Reader(db_path) as reader:
        for ip in ips:
            try:
                r = reader.city(ip)
            except (geoip2.errors.AddressNotFoundError, ValueError):
                result[ip] = {"country_code": "", "country_name": "", "region": ""}
                continue
            sub = r.subdivisions.most_specific
            region = ""
            if r.country.iso_code == "UZ":
                region = REGION_ISO.get(sub.iso_code or "", "") or normalize_region(sub.name)
            result[ip] = {
                "country_code": r.country.iso_code or "",
                "country_name": r.country.name or "",
                "region": region,
            }
    return result


def _lookup_ip_api(ips):
    """ip-api.com batch (100 tagacha IP, daqiqasiga 15 so'rov)."""
    try:
        resp = requests.post(
            "http://ip-api.com/batch?fields=status,query,countryCode,country,region,regionName",
            json=list(ips),
            timeout=10,
        )
        resp.raise_for_status()
        rows = resp.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("ip-api lookup failed: %s", exc)
        return None

    result = {}
    for row in rows:
        ip = row.get("query")
        if not ip:
            continue
        if row.get("status") != "success":
            result[ip] = {"country_code": "", "country_name": "", "region": ""}
            continue
        code = row.get("countryCode") or ""
        region = ""
        if code == "UZ":
            region = REGION_ISO.get(row.get("region") or "", "") or normalize_region(row.get("regionName"))
        result[ip] = {"country_code": code, "country_name": row.get("country") or "", "region": region}
    return result


def lookup_ips(ips):
    """IP ro'yxati -> {ip: {country_code, country_name, region}}; natija keshlanadi."""
    ips = [ip for ip in ips if ip]
    if not ips:
        return {}
    result = _lookup_maxmind(ips)
    if result is None:
        result = _lookup_ip_api(ips)
    if result is None:
        return {}
    for ip, geo in result.items():
        cache.set(GEO_CACHE_KEY.format(ip), geo, GEO_CACHE_TTL)
    return result


def visitor_ip(request):
    """
    Haqiqiy tashrifchi IP si: Cloudflare / nginx proksi sarlavhalaridan birinchi ommaviy IP.
    Proksi sarlavha yubormasa REMOTE_ADDR (odatda 127.0.0.1) qaytadi.
    """
    meta = request.META
    candidates = [meta.get("HTTP_CF_CONNECTING_IP"), meta.get("HTTP_X_REAL_IP")]
    candidates += [ip.strip() for ip in (meta.get("HTTP_X_FORWARDED_FOR") or "").split(",")]
    for ip in candidates:
        if ip and is_public_ip(ip):
            return ip
    return meta.get("REMOTE_ADDR") or None


def _lookup_ip_api_single(ip):
    """ip-api.com bitta IP (daqiqasiga 45 so'rov) — tashrif paytida darhol aniqlash uchun."""
    try:
        resp = requests.get(
            f"http://ip-api.com/json/{ip}?fields=status,countryCode,country,region,regionName",
            timeout=3,
        )
        if resp.status_code == 429:  # limit — celery keyinroq aniqlaydi
            return None
        resp.raise_for_status()
        row = resp.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("ip-api single lookup failed for %s: %s", ip, exc)
        return None
    if row.get("status") != "success":
        return {"country_code": "", "country_name": "", "region": ""}
    code = row.get("countryCode") or ""
    region = ""
    if code == "UZ":
        region = REGION_ISO.get(row.get("region") or "", "") or normalize_region(row.get("regionName"))
    return {"country_code": code, "country_name": row.get("country") or "", "region": region}


def resolve_ip(ip):
    """Bitta IP: kesh -> MaxMind -> ip-api. Aniqlanmasa None (celery qayta urinadi)."""
    geo = cached_geo(ip)
    if geo is not None:
        return geo
    result = _lookup_maxmind([ip])
    geo = result.get(ip) if result is not None else _lookup_ip_api_single(ip)
    if geo is not None:
        cache.set(GEO_CACHE_KEY.format(ip), geo, GEO_CACHE_TTL)
    return geo
