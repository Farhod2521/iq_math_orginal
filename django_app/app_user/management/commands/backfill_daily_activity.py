"""
UserDailyActivity ni mavjud tarixdan to'ldiradi (D30 retention deploydan oldingi kunlar uchun ham chiqishi uchun).
Manbalar: sayt tashriflari, ball olish tarixi, kunlik tanga, mavzu yakunlash, qurilmalar, to'lovlar.
Qayta ishga tushirsa bo'ladi — mavjud yozuvlar takrorlanmaydi.

    python manage.py backfill_daily_activity --days 120
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models.functions import TruncDate
from django.utils import timezone

from django_app.app_management.models import SiteVisit
from django_app.app_payments.models import Payment
from django_app.app_student.models import StudentDailyCoinLog, StudentScoreLog, TopicProgress
from django_app.app_user.models import UserDailyActivity, UserDevice

BATCH = 5000


class Command(BaseCommand):
    help = "Kunlik faollikni (UserDailyActivity) eski ma'lumotlardan tiklaydi"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=120, help="Necha kun orqaga (default 120)")

    def handle(self, *args, **options):
        tz = timezone.get_current_timezone()
        since = timezone.now() - timedelta(days=options["days"])
        since_date = timezone.localdate() - timedelta(days=options["days"])

        def by_datetime(qs, user_field, dt_field):
            return (qs.filter(**{f"{dt_field}__gte": since, f"{user_field}__isnull": False})
                    .annotate(d=TruncDate(dt_field, tzinfo=tz))
                    .values_list(user_field, "d").distinct())

        sources = {
            "Sayt tashriflari": by_datetime(SiteVisit.objects, "user_id", "created_at"),
            "Ball olish": by_datetime(StudentScoreLog.objects, "student_score__student__user_id", "awarded_at"),
            "Mavzu yakunlash": by_datetime(TopicProgress.objects, "user__user_id", "completed_at"),
            "Qurilma (kirish)": by_datetime(UserDevice.objects, "user_id", "created_at"),
            "Qurilma (oxirgi faollik)": by_datetime(UserDevice.objects, "user_id", "last_used_at"),
            "To'lovlar": by_datetime(Payment.objects, "student__user_id", "created_at"),
            "Kunlik tanga": (StudentDailyCoinLog.objects.filter(date__gte=since_date)
                             .values_list("student__user_id", "date").distinct()),
        }

        pairs = set()
        for name, qs in sources.items():
            rows = {(u, d) for u, d in qs.iterator() if u and d}
            pairs |= rows
            self.stdout.write(f"{name}: {len(rows)}")

        before = UserDailyActivity.objects.count()
        objs = [UserDailyActivity(user_id=u, date=d) for u, d in pairs]
        for i in range(0, len(objs), BATCH):
            UserDailyActivity.objects.bulk_create(objs[i:i + BATCH], ignore_conflicts=True)
        added = UserDailyActivity.objects.count() - before
        self.stdout.write(self.style.SUCCESS(f"Qo'shildi: {added} ta (jami {len(pairs)} ta juftlik ko'rildi)"))
