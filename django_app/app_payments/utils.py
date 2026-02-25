# utils.py

import requests
from datetime import timedelta
from django.conf import settings
from django.utils import timezone

MULTICARD_AUTH_URL = "https://mesh.multicard.uz/auth"
APPLICATION_ID = "raqamli_iqtisodiyot_va_agrotexnologiyalar_universiteti"
SECRET_KEY = "b7lydo1mu8abay9x"


# MULTICARD_AUTH_URL = "https://mesh.multicard.uz/auth"
# APPLICATION_ID = "udea"
# SECRET_KEY = "n4eci720czqjlo2t"


########### TESTIVIY ########################
# MULTICARD_AUTH_URL = "https://dev-mesh.multicard.uz/auth"
# APPLICATION_ID = "rhmt_test"
# SECRET_KEY = "Pw18axeBFo8V7NamKHXX"


def get_multicard_token():
    response = requests.post(MULTICARD_AUTH_URL, json={
        "application_id": APPLICATION_ID,
        "secret": SECRET_KEY
    })
    if response.status_code == 200:
        return response.json().get("token")
    else:
        raise Exception("Multicard token olishda xatolik yuz berdi")


def get_payment_pending_timeout_minutes():
    """Pending payment uchun timeout qiymatini qaytaradi."""
    value = getattr(settings, "PAYMENT_PENDING_TIMEOUT_MINUTES", 10)
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        minutes = 10
    return max(minutes, 1)


def expire_pending_payments(student=None):
    """
    Timeoutdan oshgan pending paymentlarni failed holatiga o'tkazadi.
    `student` berilsa, faqat shu studentning paymentlari tekshiriladi.
    """
    from .models import Payment  # Local import to avoid circular imports.

    now = timezone.now()
    cutoff = now - timedelta(minutes=get_payment_pending_timeout_minutes())
    qs = Payment.objects.filter(status="pending", created_at__lt=cutoff)
    if student is not None:
        qs = qs.filter(student=student)

    return qs.update(status="failed", updated_at=now)
