import logging

from celery import shared_task

from .utils import (
    delete_unpaid_payments,
    expire_pending_payments,
    get_payment_pending_timeout_minutes,
)


logger = logging.getLogger(__name__)


@shared_task(name="django_app.app_payments.tasks.expire_pending_payments_task")
def expire_pending_payments_task():
    """
    Har ishga tushganda timeoutdan oshgan pending paymentlarni failed qiladi.
    """
    updated_count = expire_pending_payments()
    deleted_count = delete_unpaid_payments()
    timeout_minutes = get_payment_pending_timeout_minutes()

    if updated_count or deleted_count:
        logger.info(
            "Expired pending payments: %s (timeout=%s min), deleted unpaid: %s",
            updated_count,
            timeout_minutes,
            deleted_count,
        )

    return {
        "expired_payments": updated_count,
        "deleted_unpaid_payments": deleted_count,
        "timeout_minutes": timeout_minutes,
    }
