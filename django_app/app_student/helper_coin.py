from django.utils.timezone import localdate
from .models import StudentScoreLog, StudentDailyCoinLog
from django_app.app_management.models import DailyCoinSettings


def get_daily_coin_limit():
    """Kunlik tanga chegrasini admin sozlamasidan olish. Yo'q bo'lsa 10 qaytaradi."""
    settings = DailyCoinSettings.objects.first()
    return settings.daily_coin_limit if settings else 10


def get_today_coin_count(student_score):
    """StudentScoreLog orqali bugungi yig'ilgan tanga sonini olish (mahalliy vaqt bo'yicha)."""
    today = localdate()
    return StudentScoreLog.objects.filter(
        student_score=student_score,
        award_type='coin',
        awarded_at__date=today
    ).count()


def get_or_create_daily_log(student):
    """Bugungi StudentDailyCoinLog ni olish yoki yangi yaratish (mahalliy vaqt bo'yicha)."""
    today = localdate()
    log, _ = StudentDailyCoinLog.objects.get_or_create(
        student=student,
        date=today,
        defaults={'coin_count': 0}
    )
    return log
