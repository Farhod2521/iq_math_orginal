"""
O'quvchining kunlik kirish seriyasi (🔥 "N kun").

POST /api/v1/func_student/streak/            — bugungi kirishni belgilaydi (kuniga bitta yozuv)
GET  /api/v1/func_student/streak/?year&month — seriya va oy bo'yicha kirgan kunlar (kalendar uchun)

Yangi jadval kerak emas: kirishlar StudentLoginHistory'da saqlanadi. Kun Toshkent vaqti bo'yicha olinadi.
"""
import calendar
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_app.app_user.models import Student, StudentLoginHistory

TZ = ZoneInfo("Asia/Tashkent")
LOOKBACK_DAYS = 400  # seriya va eng uzun seriyani hisoblash uchun


def _visit_dates(student, since):
    return set(
        StudentLoginHistory.objects.filter(student=student, login_time__gte=since)
        .annotate(day=TruncDate("login_time", tzinfo=TZ))
        .values_list("day", flat=True)
        .distinct()
    )


def _current_streak(dates, today):
    # Bugun hali kirilmagan bo'lsa, seriya kechagi kundan sanaladi (uzilmagan hisoblanadi)
    day = today if today in dates else today - timedelta(days=1)
    count = 0
    while day in dates:
        count += 1
        day -= timedelta(days=1)
    return count


def _best_streak(dates):
    best = run = 0
    previous = None
    for day in sorted(dates):
        run = run + 1 if previous and day - previous == timedelta(days=1) else 1
        best = max(best, run)
        previous = day
    return best


class StudentStreakAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _student(self, request):
        return Student.objects.filter(user=request.user).first()

    def _payload(self, student, request):
        today = timezone.now().astimezone(TZ).date()
        since = datetime.combine(today - timedelta(days=LOOKBACK_DAYS), datetime.min.time(), tzinfo=TZ)
        dates = _visit_dates(student, since)

        try:
            year = int(request.query_params.get("year", today.year))
            month = int(request.query_params.get("month", today.month))
            if not (1 <= month <= 12 and 2000 <= year <= 2100):
                raise ValueError
        except (TypeError, ValueError):
            year, month = today.year, today.month

        # Tanlangan oydagi kirgan kunlar (eski oylar uchun alohida so'rov)
        month_start = datetime(year, month, 1, tzinfo=TZ)
        month_end = month_start + timedelta(days=calendar.monthrange(year, month)[1])
        if month_start < since:
            month_dates = _visit_dates(student, month_start)
        else:
            month_dates = dates
        days = sorted(d.isoformat() for d in month_dates if month_start.date() <= d < month_end.date())

        return {
            "streak": _current_streak(dates, today),
            "best_streak": _best_streak(dates),
            "visited_today": today in dates,
            "today": today.isoformat(),
            "year": year,
            "month": month,
            "days": days,
        }

    def get(self, request):
        student = self._student(request)
        if not student:
            return Response({"detail": "Faqat o'quvchilar uchun."}, status=status.HTTP_403_FORBIDDEN)
        return Response(self._payload(student, request))

    def post(self, request):
        student = self._student(request)
        if not student:
            return Response({"detail": "Faqat o'quvchilar uchun."}, status=status.HTTP_403_FORBIDDEN)
        today = timezone.now().astimezone(TZ).date()
        day_start = datetime.combine(today, datetime.min.time(), tzinfo=TZ)
        # Kuniga faqat bitta kirish yoziladi (login paytida yozilgan bo'lsa — yangisi qo'shilmaydi)
        if not StudentLoginHistory.objects.filter(student=student, login_time__gte=day_start).exists():
            StudentLoginHistory.objects.create(student=student)
        return Response(self._payload(student, request))
