"""
Kundalik kirish mukofoti (gol).

Har kuni saytga kirganda (frontend avtomatik claim qiladi, tugma yo'q) +1 gol qo'shiladi (ball emas).
Ketma-ketlik 1..7 kun kartalarida ko'rsatiladi: bir kun o'tkazib yuborilsa — 1-kundan qayta,
7-kundan keyin (8-kun) yangi hafta yana 1-kundan boshlanadi. Har kuni gol bir xil: +1.

Har bir mukofot StudentPointLog'ga (gol tarixi) yoziladi: manba, nechanchi kun, necha gol, jami gol.

GET  /api/v1/func_student/daily-reward/        — holat (modal uchun)
POST /api/v1/func_student/daily-reward/claim/  — bugungi mukofotni olish
GET  /api/v1/func_student/my-gol-log/          — o'quvchining gol tarixi
"""
from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_app.app_student.gol import award_gol
from django_app.app_student.models import StudentPointLog, StudentScore

# Ketma-ketlik kuni → gol: har kuni +1 gol (kopayib bormaydi)
DAILY_GOLS = [1, 1, 1, 1, 1, 1, 1]
CYCLE_DAYS = len(DAILY_GOLS)
SOURCE = StudentPointLog.SOURCE_DAILY_LOGIN


def _student(request):
    return getattr(request.user, "student_profile", None)


def _logs(student):
    return StudentPointLog.objects.filter(student=student, source=SOURCE)


def _state(student, today):
    """
    Bugungi holat:
      claimed  — bugun olinganmi
      anchor   — joriy ketma-ketlikning oxirgi yozuvi (bugungi yoki kechagi), yo'q bo'lsa None
      day      — bugun olinadigan (yoki olingan) kun raqami (1..7)
    """
    today_log = _logs(student).filter(date=today).first()
    if today_log:
        return True, today_log, today_log.streak_day or 1

    yesterday_log = _logs(student).filter(date=today - timedelta(days=1)).first()
    if yesterday_log and (yesterday_log.streak_day or 0) < CYCLE_DAYS:
        return False, yesterday_log, (yesterday_log.streak_day or 0) + 1
    # Kecha kirmagan yoki 7 kun tugagan — 1-kundan
    return False, None, 1


def _payload(student, today):
    claimed, anchor, day_number = _state(student, today)
    streak = (anchor.streak_day or 0) if anchor else 0

    # Joriy hafta (ketma-ketlik) davomida to'plangan gol
    week_total = 0
    if anchor:
        start = anchor.date - timedelta(days=(anchor.streak_day or 1) - 1)
        week_total = sum(_logs(student).filter(date__gte=start, date__lte=anchor.date).values_list("gol", flat=True))

    days = []
    for index, gol in enumerate(DAILY_GOLS, start=1):
        if index <= streak:
            state = "claimed"
        elif index == day_number and not claimed:
            state = "today"
        else:
            state = "locked"
        days.append({"day": index, "gol": gol, "state": state})

    gol_total = StudentScore.objects.filter(student=student).values_list("gol", flat=True).first() or 0
    return {
        "claimed_today": claimed,
        "today_day": day_number,
        "today_gol": DAILY_GOLS[day_number - 1],
        "streak": streak,
        "week_total": week_total,
        "gol_total": gol_total,
        "days": days,
    }


class DailyLoginRewardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = _student(request)
        if student is None:
            return Response({"detail": "Faqat o'quvchilar uchun."}, status=status.HTTP_403_FORBIDDEN)
        return Response(_payload(student, timezone.localdate()))


class DailyLoginRewardClaimAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        student = _student(request)
        if student is None:
            return Response({"detail": "Faqat o'quvchilar uchun."}, status=status.HTTP_403_FORBIDDEN)

        today = timezone.localdate()
        awarded = 0
        claimed, _anchor, day_number = _state(student, today)
        if not claimed:
            log = award_gol(
                student.id,
                SOURCE,
                DAILY_GOLS[day_number - 1],
                date=today,
                streak_day=day_number,
                comment=f"Saytga ketma-ket {day_number}-kun kirdingiz",
            )
            awarded = log.gol if log else 0

        data = _payload(student, today)
        data["awarded"] = awarded
        return Response(data, status=status.HTTP_200_OK)


class GolLogPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class MyGolLogAPIView(APIView):
    """O'quvchining gol tarixi: qayerdan (manba), qachon va qancha gol olgani."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = _student(request)
        if student is None:
            return Response({"detail": "Faqat o'quvchilar uchun."}, status=status.HTTP_403_FORBIDDEN)

        logs = StudentPointLog.objects.filter(student=student).order_by("-created_at")
        source = request.query_params.get("source")
        if source:
            logs = logs.filter(source=source)

        paginator = GolLogPagination()
        page = paginator.paginate_queryset(logs, request, view=self)
        rows = [
            {
                "id": log.id,
                "source": log.source,
                "source_display": log.get_source_display(),
                "gol": log.gol,
                "gol_after": log.gol_after,
                "streak_day": log.streak_day,
                "ref": log.ref,
                "comment": log.comment,
                "date": log.date,
                "created_at": log.created_at,
            }
            for log in page
        ]
        response = paginator.get_paginated_response(rows)
        response.data["gol_total"] = (
            StudentScore.objects.filter(student=student).values_list("gol", flat=True).first() or 0
        )
        return response
