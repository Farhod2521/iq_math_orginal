"""
Gol — balldan (StudentScore.score) alohida hisob. Jami: StudentScore.gol, tarixi: StudentPointLog.

Manbalar:
  - Kundalik kirish (daily_login_reward.py): har kuni kirganda +1 gol (ketma-ketlik 1..7 kun)
  - Haftalik test (app_liga.services._finalize): test natijasi (to'g'ri javoblar balli) → shuncha gol
  - Mavzu misollari (views.py, javoblarni tekshirish): olingan tanga soniga teng gol (1 tanga = 1 gol).
    Tanga kunlik chegarali (DailyCoinSettings), chegara to'lgach ball beriladi va gol qo'shilmaydi.

Gol faqat ligaga qo'shilgan o'quvchiga yig'iladi (is_liga_joined).
"""
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import StudentPointLog, StudentScore
from .wallet import Log, log_wallet

LESSON_GOL_PER_COIN = 1
LESSON_GOL_PER_QUESTION = LESSON_GOL_PER_COIN  # eski nom — boshqa joylar buzilmasin


def is_liga_joined(student_id):
    """Gol yig'ish faqat ligaga qo'shilgandan keyin: ochiq mavsum ishtirokchisi bo'lishi kerak."""
    # Ichkarida import: app_liga.services shu modulni import qiladi
    from django_app.app_liga.models import LigaParticipant

    return LigaParticipant.objects.filter(
        student_id=student_id, season__closed_at__isnull=True, season__is_published=True,
    ).exists()


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
            log = StudentPointLog.objects.create(
                student_id=student_id,
                source=source,
                gol=gol,
                date=date,
                ref=str(ref) if ref else "",
                streak_day=streak_day,
                gol_after=score.gol,
                comment=comment[:255],
            )
            # Umumiy hamyon tarixiga ham (manba nomlari bir xil: daily_login / weekly_test)
            log_wallet(student_id, Log.CURRENCY_GOL, gol, source, comment, balance_after=score.gol, ref=f"gol:{log.id}")
            return log
    except IntegrityError:
        return None
