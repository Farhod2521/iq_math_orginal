"""
Foydalanuvchilar bo'yicha oylik hisobot (o'qituvchi panelidagi "PPTX hisobot" uchun).

GET /api/v1/auth/student/monthly-report/?year=2026&month=9
Tanlangan oy va undan oldingi oyda ro'yxatdan o'tganlar (User.date_joined) soni
rollar bo'yicha, kunlik dinamika va yangi o'quvchilarning sinf / qurilma / til /
diagnostika kesimi. Oy chegaralari Toshkent vaqti bo'yicha olinadi.
"""
import calendar
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

from django.db.models import Count, Q
from django.db.models.functions import ExtractDay
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_app.app_student.models import Diagnost_Student
from django_app.app_user.all_role_listview import All_Role_ListView
from django_app.app_user.models import User

# zoneinfo (pytz emas): Django 5 da pytz zonasi ExtractDay'ga "LMT" nomi bilan
# uzatilib, PostgreSQL uni tanimaydi va so'rov 500 bilan tushadi.
TZ = ZoneInfo("Asia/Tashkent")
ROLES = ("student", "parent", "tutor", "teacher")


def _month_range(year, month):
    start = datetime(year, month, 1, tzinfo=TZ)
    end = datetime(year + 1, 1, 1, tzinfo=TZ) if month == 12 else datetime(year, month + 1, 1, tzinfo=TZ)
    return start, end


def _previous(year, month):
    return (year - 1, 12) if month == 1 else (year, month - 1)


def _role_counts(queryset):
    return queryset.aggregate(**{role: Count("id", filter=Q(role=role)) for role in ROLES})


def _device_group(value):
    value = (value or "").lower()
    for key in ("android", "ios", "web", "mobile"):
        if value.startswith(key):
            return key
    return "other" if value else "unknown"


class MonthlyUsersReportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = datetime.now(TZ)
        try:
            year = int(request.GET.get("year", today.year))
            month = int(request.GET.get("month", today.month))
            if not 1 <= month <= 12 or not 2000 <= year <= 2100:
                raise ValueError
        except (TypeError, ValueError):
            return Response({"detail": "year/month noto'g'ri"}, status=400)

        start, end = _month_range(year, month)
        prev_year, prev_month = _previous(year, month)
        prev_start, prev_end = _month_range(prev_year, prev_month)

        current_qs = User.objects.filter(date_joined__gte=start, date_joined__lt=end)
        previous_qs = User.objects.filter(date_joined__gte=prev_start, date_joined__lt=prev_end)

        current = _role_counts(current_qs)
        previous = _role_counts(previous_qs)

        # Kunlik dinamika (rollar bo'yicha)
        days_in_month = calendar.monthrange(year, month)[1]
        daily = {day: {role: 0 for role in ROLES} for day in range(1, days_in_month + 1)}
        rows = (
            current_qs.filter(role__in=ROLES)
            .annotate(day=ExtractDay("date_joined", tzinfo=TZ))
            .values("day", "role")
            .annotate(count=Count("id"))
        )
        for row in rows:
            if row["day"] in daily:
                daily[row["day"]][row["role"]] = row["count"]

        # Yangi o'quvchilar kesimi
        new_students = current_qs.filter(role="student")
        by_class = (
            new_students.values("student_profile__class_name__classes__name")
            .annotate(count=Count("id"))
        )
        class_counter = Counter()
        for row in by_class:
            name = row["student_profile__class_name__classes__name"] or "—"
            class_counter[name] += row["count"]

        device_counter = Counter(_device_group(value) for value in new_students.values_list("device", flat=True))
        lang_counter = Counter(
            (value or "uz").lower() for value in new_students.values_list("student_profile__lang", flat=True)
        )
        # Diagnost_Student.student da related_name yo'q — to'g'ridan-to'g'ri jadvaldan sanaymiz
        with_diagnostic = (
            Diagnost_Student.objects.filter(student__user__in=new_students)
            .values("student_id")
            .distinct()
            .count()
        )

        def sort_class(item):
            name = item[0]
            return (0, int(name)) if str(name).isdigit() else (1, str(name))

        # Shu oyda ro'yxatdan o'tganlarning to'liq ro'yxati (Word hisobot jadvali uchun).
        # Ustunlar "Foydalanuvchilar" sahifasidagi jadval bilan bir xil — qiymatlar o'sha
        # All_Role_ListView mantiqidan olinadi (holat, diagnostika, obuna, oxirgi kirish...).
        joined = list(
            current_qs.filter(role__in=ROLES)
            .select_related(
                "student_profile__class_name__classes",
                "student_profile__subscription",
                "parent_profile",
                "teacher_profile",
                "tutor_profile",
            )
            .order_by("date_joined", "id")
        )
        lister = All_Role_ListView()
        lookups = lister.build_lookups(joined)
        users = []
        for user in joined:
            info = lister.get_profile_data(user, TZ, lookups).get("json", {})
            users.append({
                "full_name": info.get("full_name") or "",
                "role": user.role,
                "phone": user.phone or "",
                "status": bool(info.get("status")),
                "has_diagnost": bool(info.get("has_diagnost")),
                "completed_today": bool(info.get("completed_today")),
                "class_num": info.get("class_num") or "",
                "subject_name_uz": info.get("subject_name_uz") or "",
                "subject_name_ru": info.get("subject_name_ru") or "",
                "subscription_end_date": info.get("subscription_end_date") or "",
                "remaining_days": info.get("remaining_days"),
                "lang": (info.get("lang") or "").upper(),
                "device": user.device or "",
                "last_login_time": info.get("last_login_time") or "",
                "date": user.date_joined.astimezone(TZ).strftime("%d.%m.%Y %H:%M") if user.date_joined else "",
            })

        return Response({
            "users": users,
            "period": {"year": year, "month": month, "days": days_in_month},
            "previous_period": {"year": prev_year, "month": prev_month},
            "current": current,
            "previous": previous,
            "total_current": sum(current.values()),
            "total_previous": sum(previous.values()),
            "all_time": _role_counts(User.objects.all()),
            "daily": [{"day": day, **counts} for day, counts in daily.items()],
            "students": {
                "total": current["student"],
                "with_diagnostic": with_diagnostic,
                "by_class": [{"name": name, "count": count} for name, count in sorted(class_counter.items(), key=sort_class)],
                "by_device": [{"name": name, "count": count} for name, count in device_counter.most_common()],
                "by_lang": [{"name": name, "count": count} for name, count in lang_counter.most_common()],
            },
            "generated_at": today.strftime("%d.%m.%Y %H:%M"),
        })
