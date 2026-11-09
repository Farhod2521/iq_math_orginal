"""
Hamyon tarixi (StudentWalletLog) — ball, tanga, so'm va gol bo'yicha har bir kirim/chiqim.

Balans o'zgaradigan joyda balans saqlangandan keyin chaqiriladi:
    log_wallet(student_id, "coin", +5, "lesson", "“Kasrlar” mavzusi: 5 ta to'g'ri javob", balance_after=score.coin)
Tarix yozilmay qolsa ham asosiy amal buzilmasin — xato faqat logga yoziladi.
"""
import logging

from django.db import transaction

from .models import StudentWalletLog

logger = logging.getLogger(__name__)

Log = StudentWalletLog  # qisqa nom: Log.CURRENCY_COIN, Log.SOURCE_LESSON ...


def log_wallet(student_id, currency, amount, source, description="", *, balance_after=None, ref=""):
    amount = int(amount or 0)
    if not student_id or amount == 0:
        return None
    try:
        # Savepoint: yozuv xatosi tashqi tranzaksiyani buzmasin
        with transaction.atomic():
            return StudentWalletLog.objects.create(
                student_id=student_id,
                currency=currency,
                source=source,
                amount=amount,
                balance_after=balance_after,
                description=(description or "")[:255],
                ref=str(ref)[:50] if ref else "",
            )
    except Exception:  # noqa: BLE001 — tarix asosiy amalni to'xtatmasin
        logger.exception("Hamyon tarixini yozib bo'lmadi: student=%s %s %s", student_id, currency, amount)
        return None
