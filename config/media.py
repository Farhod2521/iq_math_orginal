"""Yuklangan fayllarni (rasm, video, hujjat) xavfsiz berish.

Oldin `static(settings.MEDIA_URL, ...)` DEBUG=True bilan ishlagan va MEDIA_URL bo'sh
bo'lgani uchun loyiha papkasidagi HAR QANDAY faylni (.env, serviceAccountKey.json,
manba kodi) tashqariga berib yuborgan. Bu view faqat yuklangan media fayllarni beradi:
  - fayl albatta biror papka ichida bo'lishi kerak (ildizdagi fayllar berilmaydi);
  - kod/sozlama papkalari va yashirin (nuqta bilan boshlanuvchi) yo'llar yopiq;
  - faqat ruxsat etilgan kengaytmalar (rasm, video, audio, hujjat).
Fayl manzillari o'zgarmaydi: /elon_images/..., /question_images/..., /FILES/... avvalgidek ishlaydi.
"""
import os
import posixpath

from django.conf import settings
from django.http import Http404
from django.views.static import serve

ALLOWED_EXTENSIONS = {
    # rasmlar
    '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp', '.ico', '.avif', '.heic',
    # video / audio
    '.mp4', '.webm', '.mov', '.m4v', '.mp3', '.wav', '.ogg', '.m4a',
    # hujjatlar
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
}

# Yuklangan fayl saqlanmaydigan, tashqariga berilmasligi kerak bo'lgan papkalar
BLOCKED_TOP_DIRS = {
    'config', 'django_app', 'fastapi_app', 'bot_telegram', 'telegram_bot', 'templates',
    'static', 'staticfiles', 'iq_math_orginal', 'graphify-out', 'locale', 'testdoc',
    'node_modules', 'venv', 'env', 'logs',
}


def media_serve(request, path):
    normalized = posixpath.normpath(path.replace('\\', '/')).lstrip('/')
    parts = [p for p in normalized.split('/') if p]

    if len(parts) < 2:
        raise Http404()
    if any(p.startswith('.') or p.startswith('__') for p in parts):
        raise Http404()
    if parts[0].lower() in BLOCKED_TOP_DIRS:
        raise Http404()
    if os.path.splitext(parts[-1])[1].lower() not in ALLOWED_EXTENSIONS:
        raise Http404()

    # MEDIA_ROOT bo'sh bo'lsa — avvalgidek, jarayon ishlayotgan papka (loyiha ildizi)
    document_root = os.path.abspath(settings.MEDIA_ROOT or '')
    return serve(request, '/'.join(parts), document_root=document_root)
