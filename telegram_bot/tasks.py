from celery import shared_task

from .backup import run_backup
from .marketing import notify_new_students


@shared_task(name="telegram_bot.notify_new_students")
def notify_new_students_task():
    return notify_new_students()


# Katta backup soatlab davom etishi mumkin — Celery vaqt chegarasi bilan uzilib qolmasin
@shared_task(name="telegram_bot.daily_backup", time_limit=None, soft_time_limit=None)
def daily_backup_task():
    return run_backup()
