"""
O'quvchining hamyon tarixi — "Tarix" sahifasi uchun.

GET /api/v1/func_student/wallet-history/
    ?currency=gol|score|coin|som   — tur bo'yicha filtr (bo'sh — barchasi)
    ?date_from=2026-11-01&date_to=2026-11-09   — sana oralig'i (Toshkent vaqti, ikkalasi ham kiradi)
    ?page=1&page_size=20

Javob:
{
  "summary": {"gol": 1, "som": 0, "coin": 55, "score": 93},   — joriy balanslar (kartochkalar)
  "count": 8, "next": ..., "previous": ...,
  "results": [{
      "id", "created_at", "source", "source_display", "description",
      "currency", "currency_display", "amount" (kirim +, chiqim −), "balance_after" (null bo'lishi mumkin)
  }]
}
"""
from datetime import datetime, time, timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_app.app_student.models import StudentScore, StudentWalletLog

CURRENCIES = {key for key, _ in StudentWalletLog.CURRENCY_CHOICES}


class WalletHistoryPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def _parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _day_start(day):
    return timezone.make_aware(datetime.combine(day, time.min))


class WalletHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = getattr(request.user, "student_profile", None)
        if student is None:
            return Response({"detail": "Faqat o'quvchilar uchun."}, status=status.HTTP_403_FORBIDDEN)

        logs = StudentWalletLog.objects.filter(student=student)

        currency = request.query_params.get("currency")
        if currency in CURRENCIES:
            logs = logs.filter(currency=currency)

        date_from = _parse_date(request.query_params.get("date_from"))
        date_to = _parse_date(request.query_params.get("date_to"))
        if date_from:
            logs = logs.filter(created_at__gte=_day_start(date_from))
        if date_to:
            logs = logs.filter(created_at__lt=_day_start(date_to + timedelta(days=1)))

        paginator = WalletHistoryPagination()
        page = paginator.paginate_queryset(logs.order_by("-created_at", "-id"), request, view=self)
        rows = [
            {
                "id": log.id,
                "created_at": timezone.localtime(log.created_at).isoformat(),
                "source": log.source,
                "source_display": log.get_source_display(),
                "description": log.description,
                "currency": log.currency,
                "currency_display": log.get_currency_display(),
                "amount": log.amount,
                "balance_after": log.balance_after,
            }
            for log in page
        ]

        balance = StudentScore.objects.filter(student=student).values("gol", "som", "coin", "score").first() or {}
        response = paginator.get_paginated_response(rows)
        response.data["summary"] = {
            "gol": balance.get("gol", 0),
            "som": balance.get("som", 0),
            "coin": balance.get("coin", 0),
            "score": balance.get("score", 0),
        }
        return response
