"""
Gol — balldan (StudentScore.score) alohida hisob. Jami: StudentScore.gol, tarixi: StudentPointLog.

Manbalar:
  - Kundalik kirish (daily_login_reward.py): ketma-ketlik kuni 1..7 → 1..7 gol
  - Haftalik test (app_liga.services._finalize): test natijasi (to'g'ri javoblar balli) → shuncha gol
"""
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import StudentPointLog, StudentScore


def award_gol(student_id, source, gol, *, ref="", date=None, streak_day=None, comment=""):
    """
    O'quvchiga gol qo'shadi va tarixga yozadi. Takroriy chaqiruv (o'sha kun / o'sha ref) gol qo'shmaydi.
    Qaytaradi: yaratilgan StudentPointLog yoki None (gol 0 bo'lsa yoki allaqachon berilgan bo'lsa).
    """
    gol = int(gol or 0)
    if gol <= 0:
        return None
    date = date or timezone.localdate()
    try:
        with transaction.atomic():
            # Bir vaqtda ikki so'rov kelsa — gol ikki marta qo'shilmasin
            score, _ = StudentScore.objects.select_for_update().get_or_create(student_id=student_id)
            duplicate = StudentPointLog.objects.filter(student_id=student_id, source=source)
            duplicate = duplicate.filter(ref=str(ref)) if ref else duplicate.filter(date=date)
            if duplicate.exists():
                return None
            score.gol += gol
            score.save(update_fields=["gol"])
            return StudentPointLog.objects.create(
                student_id=student_id,
                source=source,
                gol=gol,
                date=date,
                ref=str(ref) if ref else "",
                streak_day=streak_day,
                gol_after=score.gol,
                comment=comment[:255],
            )
    except IntegrityError:
        return None
