"""
Admin panel bosh sahifasi uchun dinamika:
  GET /api/v1/management/statistics/overview/?days=7   (days: 7 | 14 | 30)

  trends   — kartochkalar uchun: oxirgi 30 kun va undan oldingi 30 kun solishtiruvi (foiz)
             hamda 8 haftalik kichik grafik (spark) qiymatlari
  activity — kunma-kun: yangi o'quvchilar, muvaffaqiyatli to'lovlar, faol foydalanuvchilar
"""
from datetime import datetime, time, timedelta

from django.core.cache import cache
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from django_app.app_management.permissions import IsTeacherOrSuperAdmin
from django_app.app_payments.models import Payment
from django_app.app_user.models import Parent, Student, Teacher, Tutor, UserDailyActivity

WEEKS = 8
CACHE_TTL = 300


def _pct_change(current, previous):
    if not previous:
        return 100.0 if current else 0.0
    return round((current - previous) * 100 / previous, 1)


class DashboardOverviewAPIView(APIView):
    permission_classes = [IsTeacherOrSuperAdmin]

    def get(self, request):
        try:
            days = int(request.query_params.get("days", 7))
        except ValueError:
            days = 7
        days = days if days in (7, 14, 30) else 7
        today = timezone.localdate()
        data = cache.get_or_set(
            f"dashboard_overview:{today.isoformat()}:{days}",
            lambda: {"trends": self._trends(), "activity": self._activity(days)},
            CACHE_TTL,
        )
        return Response(data)

    # ---------- kartochkalar ----------

    def _trends(self):
        now = timezone.now()
        d30, d60 = now - timedelta(days=30), now - timedelta(days=60)
        week_ends = [now - timedelta(weeks=i) for i in range(WEEKS - 1, -1, -1)]

        def people(model):
            # Jami soni o'sishi: hozir va 30 kun oldingi holat; spark — har hafta oxiridagi jami
            qs = model.objects.filter(status=True)
            total = qs.count()
            before = qs.filter(user__date_joined__lt=d30).count()
            spark = [qs.filter(user__date_joined__lt=end).count() for end in week_ends]
            return {"change": _pct_change(total, before), "spark": spark}

        success = Payment.objects.filter(status="success")

        def money(field):
            # Oxirgi 30 kun va undan oldingi 30 kun summasi; spark — haftalik summa
            def total(a, b):
                return float(success.filter(payment_date__gte=a, payment_date__lt=b)
                             .aggregate(s=Sum(field))["s"] or 0)
            spark = [total(end - timedelta(weeks=1), end) for end in week_ends]
            return {"change": _pct_change(total(d30, now), total(d60, d30)), "spark": spark}

        def payers(a, b):
            return success.filter(payment_date__gte=a, payment_date__lt=b).values("student").distinct().count()

        return {
            "teachers": people(Teacher),
            "students": people(Student),
            "parents": people(Parent),
            "tutors": people(Tutor),
            "revenue": money("amount"),
            "student_cashback": money("student_cashback_amount"),
            "teacher_cashback": money("teacher_cashback_amount"),
            "subscribers": {
                "change": _pct_change(payers(d30, now), payers(d60, d30)),
                "spark": [payers(end - timedelta(weeks=1), end) for end in week_ends],
            },
            "payments": {
                "change": _pct_change(
                    success.filter(payment_date__gte=d30).count(),
                    success.filter(payment_date__gte=d60, payment_date__lt=d30).count(),
                ),
                "spark": [success.filter(payment_date__gte=end - timedelta(weeks=1), payment_date__lt=end).count()
                          for end in week_ends],
            },
        }

    # ---------- platforma faolligi ----------

    def _activity(self, days):
        tz = timezone.get_current_timezone()
        end_date = timezone.localdate()
        start_date = end_date - timedelta(days=days - 1)
        start = timezone.make_aware(datetime.combine(start_date, time.min), tz)

        def by_day(qs, field):
            return dict(
                qs.filter(**{f"{field}__gte": start})
                .annotate(d=TruncDate(field, tzinfo=tz)).values("d")
                .annotate(c=Count("id")).values_list("d", "c")
            )

        students = by_day(Student.objects.all(), "user__date_joined")
        payments = by_day(Payment.objects.filter(status="success"), "payment_date")
        active = dict(
            UserDailyActivity.objects.filter(date__gte=start_date, date__lte=end_date)
            .values("date").annotate(c=Count("user", distinct=True)).values_list("date", "c")
        )

        series = []
        for i in range(days):
            d = start_date + timedelta(days=i)
            series.append({
                "date": d,
                "new_students": students.get(d, 0),
                "payments": payments.get(d, 0),
                "active_users": active.get(d, 0),
            })
        return series
