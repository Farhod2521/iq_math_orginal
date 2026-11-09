"""
Kundalik kirish mukofoti.

Har kuni saytga kirib "Bugungi mukofotni olish" bosilganda ball (StudentScore.score) qo'shiladi:
    1-kun → +1, 2-kun → +2, ... 7-kun → +7 ball.
Bir kun o'tkazib yuborilsa — ketma-ketlik 1-kundan qayta boshlanadi.
7-kundan keyin yangi hafta 1-kundan boshlanadi.

Har bir mukofot StudentPointLog'ga yoziladi (manba: daily_login) — kim, qachon, nechanchi kun,
necha ball oldi va keyingi balans.

GET  /api/v1/func_student/daily-reward/        — holat (modal uchun)
POST /api/v1/func_student/daily-reward/claim/  — bugungi mukofotni olish
"""
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_app.app_student.models import StudentPointLog, StudentScore

# Ketma-ketlik kuni → ball (1-kun 1 ball, ..., 7-kun 7 ball)
DAILY_REWARDS = [1, 2, 3, 4, 5, 6, 7]
CYCLE_DAYS = len(DAILY_REWARDS)
SOURCE = StudentPointLog.SOURCE_DAILY_LOGIN


def _student(request):
    return getattr(request.user, "student_profile", None)


def _logs(student):
    return StudentPointLog.objects.filter(student=student, source=SOURCE)


def _state(student, today):
    """
    Bugungi holat:
      claimed     — bugun olinganmi
      anchor      — joriy ketma-ketlikning oxirgi yozuvi (bugungi yoki kechagi), yo'q bo'lsa None
      next_day    — bugun olinadigan (yoki olingan) kun raqami (1..7)
    """
    today_log = _logs(student).filter(date=today).first()
    if today_log:
        return True, today_log, today_log.streak_day or 1

    yesterday_log = _logs(student).filter(date=today - timedelta(days=1)).first()
    if yesterday_log and (yesterday_log.streak_day or 0) < CYCLE_DAYS:
        return False, yesterday_log, (yesterday_log.streak_day or 0) + 1
    # Kecha kirmagan yoki hafta tugagan — 1-kundan
    return False, None, 1


def _payload(student, today):
    claimed, anchor, next_day = _state(student, today)
    streak = (anchor.streak_day or 0) if anchor else 0

    # Joriy hafta (ketma-ketlik) davomida to'plangan ball
    week_total = 0
    if anchor:
        start = anchor.date - timedelta(days=(anchor.streak_day or 1) - 1)
        week_total = sum(_logs(student).filter(date__gte=start, date__lte=anchor.date).values_list("points", flat=True))

    days = []
    for index, points in enumerate(DAILY_REWARDS, start=1):
        if index <= streak:
            state = "claimed"
        elif index == next_day and not claimed:
            state = "today"
        else:
            state = "locked"
        days.append({"day": index, "points": points, "state": state})

    score = StudentScore.objects.filter(student=student).values_list("score", flat=True).first() or 0
    return {
        "claimed_today": claimed,
        "today_day": next_day,
        "today_points": DAILY_REWARDS[next_day - 1],
        "streak": streak,
        "week_total": week_total,
        "score": score,
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
        try:
            with transaction.atomic():
                # Bir vaqtda ikki so'rov kelsa — ball ikki marta qo'shilmasin
                score, _ = StudentScore.objects.select_for_update().get_or_create(student=student)
                claimed, _anchor, day = _state(student, today)
                if not claimed:
                    awarded = DAILY_REWARDS[day - 1]
                    score.score += awarded
                    score.save(update_fields=["score"])
                    StudentPointLog.objects.create(
                        student=student,
                        source=SOURCE,
                        points=awarded,
                        date=today,
                        streak_day=day,
                        score_after=score.score,
                        comment=f"Kundalik kirish: {day}-kun",
                    )
        except IntegrityError:
            # Parallel so'rov allaqachon yozib bo'lgan
            awarded = 0

        data = _payload(student, today)
        data["awarded"] = awarded
        return Response(data, status=status.HTTP_200_OK)
