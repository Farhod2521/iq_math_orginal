from celery import shared_task

from .backup import run_backup
from .marketing import notify_new_leads, notify_new_payments, notify_new_students


@shared_task(name="telegram_bot.notify_new_students")
def notify_new_students_task():
    """Har daqiqada: yangi o'quvchilar, to'lovlar va bepul darsga arizalar marketing chatiga."""
    sent = {}
    for name, job in (("students", notify_new_students), ("payments", notify_new_payments), ("leads", notify_new_leads)):
        try:
            sent[name] = job()
        except Exception as exc:  # biri xato bersa qolganlari baribir ishlasin
            sent[name] = f"xato: {exc}"
    return sent


# Katta backup soatlab davom etishi mumkin — Celery vaqt chegarasi bilan uzilib qolmasin
@shared_task(name="telegram_bot.daily_backup", time_limit=None, soft_time_limit=None)
def daily_backup_task():
    return run_backup()
