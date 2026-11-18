# utils.py

import requests
from datetime import timedelta
from django.conf import settings
from django.utils import timezone

MULTICARD_AUTH_URL = "https://mesh.multicard.uz/auth"
APPLICATION_ID = "raqamli_iqtisodiyot_va_agrotexnologiyalar_universiteti"
SECRET_KEY = "b7lydo1mu8abay9x"

# Multicard umumiy sozlamalari — obuna ham, kitob to'lovi ham shu qiymatlardan foydalanadi.
MULTICARD_BASE_URL = "https://mesh.multicard.uz"
MULTICARD_STORE_ID = 1915


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


def get_unpaid_payment_retention_hours():
    """To'lanmagan (pending/failed) yozuv necha soatdan keyin o'chiriladi."""
    value = getattr(settings, "PAYMENT_UNPAID_RETENTION_HOURS", 24)
    try:
        hours = int(value)
    except (TypeError, ValueError):
        hours = 24
    return max(hours, 1)


def delete_unpaid_payments():
    """
    Bazada faqat muvaffaqiyatli to'lovlar qolsin.

    Yozuv to'lov boshlanganda yaratilishi shart — Multicard callback uni
    transaction_id bo'yicha topadi (tarif, kupon, keshbek shu yozuvda). Foydalanuvchi
    kechikib to'lasa ham callback "failed" yozuvni success qiladi, shuning uchun
    yozuv darhol emas, saqlash muddati (standart 24 soat) o'tgach o'chiriladi.
    Shu vaqt ichida pending/failed yozuvlar hech qayerda ko'rsatilmaydi.
    """
    from .models import Payment  # Local import to avoid circular imports.

    cutoff = timezone.now() - timedelta(hours=get_unpaid_payment_retention_hours())
    deleted, _ = Payment.objects.filter(
        status__in=["pending", "failed"], created_at__lt=cutoff
    ).delete()
    return deleted


def plan_base_price(plan):
    """Tarifning o'z chegirmasi bilan narxi (`price_per_month` — tarifning to'liq narxi)."""
    price = float(plan.price_per_month)
    if plan.discount_percent:
        price = price * (1 - plan.discount_percent / 100)
    return price


def coupon_discount_amount(coupon_percent):
    """
    Kupon chegirmasi summasi: 1 oylik tarif narxining kupon foizi.
    Tekshirish (check-coupon) va to'lov (initiate-payment) bir xil hisoblashi uchun yagona joy.
    """
    from .models import SubscriptionPlan  # Local import to avoid circular imports.

    if not coupon_percent:
        return 0
    # Bir nechta 1 oylik tarif (Start, Start Pro) bo'lsa — eng arzoni asos qilinadi
    one_month_plan = SubscriptionPlan.objects.filter(months=1, is_active=True).order_by("price_per_month", "id").first()
    if one_month_plan is None:
        return 0
    return plan_base_price(one_month_plan) * coupon_percent / 100


# Multicard callback'idagi `ps` (to'lov tizimi) qiymatlari -> bazada saqlanadigan nom
PAYMENT_SYSTEMS = {
    "click": "click",
    "payme": "payme",
    "uzum": "uzum",
    "uzumbank": "uzum",
    "uzcard": "uzcard",
    "humo": "humo",
    "visa": "visa",
    "mastercard": "mastercard",
    "anorbank": "anorbank",
    "alif": "alif",
    "oson": "oson",
    "xazna": "xazna",
    "apelsin": "apelsin",
    "beepul": "beepul",
}


def normalize_payment_system(value):
    """Callback'dagi to'lov tizimi nomini (masalan "Click", "PAYME") bir xil ko'rinishga keltiradi."""
    if not value:
        return None
    key = str(value).strip().lower().replace(" ", "").replace("_", "")
    return PAYMENT_SYSTEMS.get(key, key[:50] or None)
