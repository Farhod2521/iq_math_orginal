import os

from celery import Celery
from celery.schedules import crontab


env = os.getenv("DJANGO_ENV", "production")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"config.settings.{env}")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
# Telegram bot (marketing xabarlari va kunlik backup) — telegram_bot/tasks.py
app.autodiscover_tasks(["telegram_bot"])

app.conf.beat_schedule = {
    "expire-pending-payments-every-minute": {
        "task": "django_app.app_payments.tasks.expire_pending_payments_task",
        "schedule": crontab(minute="*"),
    },
    "send-daily-topic-notifications": {
        "task": "send_daily_topic_notifications",
        # Har kuni soat 08:00 Toshkent vaqti.
        # Diqqat: CELERY_TIMEZONE = 'Asia/Tashkent' va CELERY_ENABLE_UTC = False
        # (config/settings/base.py), shuning uchun crontab soatlari UTC'ga emas,
        # to'g'ridan-to'g'ri Toshkent mahalliy vaqtiga nisbatan hisoblanadi.
        "schedule": crontab(hour=8, minute=0),
    },
    "resolve-site-visit-geo-every-minute": {
        "task": "django_app.app_management.tasks.resolve_site_visit_geo_task",
        "schedule": crontab(minute="*"),
    },
    # Yangi o'quvchilar haqida marketing chatiga xabar
    "telegram-new-students-every-minute": {
        "task": "telegram_bot.notify_new_students",
        "schedule": crontab(minute="*"),
    },
    # Liga: vaqti tugab, "Yakunlash"ni bosmagan o'quvchilarning natijasini yopish
    "liga-finalize-expired-attempts-every-minute": {
        "task": "django_app.app_liga.tasks.finalize_expired_attempts_task",
        "schedule": crontab(minute="*"),
    },
    # Liga: oxirgi hafta testlari tugagan mavsumni yopish va g'oliblarni e'lon qilish
    "liga-close-finished-seasons-every-minute": {
        "task": "django_app.app_liga.tasks.close_finished_seasons_task",
        "schedule": crontab(minute="*"),
    },
    # Baza va fayllar backupi admin chatiga — har kuni 03:00 (Toshkent)
    "telegram-daily-backup": {
        "task": "telegram_bot.daily_backup",
        "schedule": crontab(hour=3, minute=0),
    },
}
