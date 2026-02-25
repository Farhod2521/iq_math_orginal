from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from django_app.app_user.models import Student, Parent, Tutor
from django_app.app_payments.utils import expire_pending_payments, get_payment_pending_timeout_minutes

class Command(BaseCommand):
    help = "03:00 da status=False bo'lgan eski foydalanuvchilarni tozalaydi va timeoutdan oshgan pending Paymentlarni failed qiladi."

    def handle(self, *args, **options):
        now = timezone.now()
        cutoff_user_time = now - timedelta(minutes=5)     # Foydalanuvchilar uchun 5 daqiqa

        deleted_users = 0
        failed_payments = 0

        # -----------------------------------
        # 1️⃣ STUDENT — eski va status=False
        # -----------------------------------
        students = Student.objects.filter(status=False, student_date__lt=cutoff_user_time)
        for s in students:
            s.user.delete()
            deleted_users += 1

        # -----------------------------------
        # 2️⃣ PARENT — status=False
        # -----------------------------------
        parents = Parent.objects.filter(status=False, parent_date__lt=cutoff_user_time)
        for p in parents:
            p.user.delete()
            deleted_users += 1

        # -----------------------------------
        # 3️⃣ TUTOR — status=False
        # -----------------------------------
        tutors = Tutor.objects.filter(status=False, tutor_date__lt=cutoff_user_time)
        for t in tutors:
            t.user.delete()
            deleted_users += 1

        # -----------------------------------------------
        # 4️⃣ PAYMENT — 10+ daqiqa pending bo‘lib qolganlar
        # -----------------------------------------------
        failed_payments = expire_pending_payments()

        # -----------------------------------------------
        # Natijani chiqaramiz
        # -----------------------------------------------
        self.stdout.write(self.style.SUCCESS(
            f"{deleted_users} ta foydalanuvchi o'chirildi."
        ))
        self.stdout.write(self.style.SUCCESS(
            f"{failed_payments} ta pending Payment "
            f"({get_payment_pending_timeout_minutes()}+ daqiqa) failed holatiga o'tkazildi."
        ))
