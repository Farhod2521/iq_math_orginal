from django.utils.timezone import now
from .models import StudentScoreLog
def get_today_coin_count(student_score):
    today = now().date()
    return StudentScoreLog.objects.filter(
        student_score=student_score,
        awarded_coin=True,
        awarded_at__date=today
    ).count()