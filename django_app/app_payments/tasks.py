import logging

from celery import shared_task

from .utils import expire_pending_payments, get_payment_pending_timeout_minutes


logger = logging.getLogger(__name__)


@shared_task(name="django_app.app_payments.tasks.expire_pending_payments_task")
def expire_pending_payments_task():
    """
    Har ishga tushganda timeoutdan oshgan pending paymentlarni failed qiladi.
    """
    updated_count = expire_pending_payments()
    timeout_minutes = get_payment_pending_timeout_minutes()

    if updated_count:
        logger.info(
            "Expired pending payments: %s (timeout=%s min)",
            updated_count,
            timeout_minutes,
        )

    return {
        "expired_payments": updated_count,
        "timeout_minutes": timeout_minutes,
    }
