from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from django_app.app_user.models import Student, Parent, Tutor
from django_app.app_payments.models import Payment   # <-- Payment modelni import qilish

class Command(BaseCommand):
    help = "03:00 da status=False bo'lgan eski foydalanuvchilarni va 10 daqiqadan ortiq pending Paymentlarni o'chiradi."

    def handle(self, *args, **options):
        now = timezone.now()
        cutoff_user_time = now - timedelta(minutes=5)     # Foydalanuvchilar uchun 5 daqiqa
        cutoff_payment_time = now - timedelta(minutes=10) # Payment uchun 10 daqiqa

        deleted_users = 0
        deleted_payments = 0

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
        pending_payments = Payment.objects.filter(
            status="pending", 
            created_at__lt=cutoff_payment_time
        )

        deleted_payments = pending_payments.count()
        pending_payments.delete()

        # -----------------------------------------------
        # Natijani chiqaramiz
        # -----------------------------------------------
        self.stdout.write(self.style.SUCCESS(
            f"{deleted_users} ta foydalanuvchi o'chirildi."
        ))
        self.stdout.write(self.style.SUCCESS(
            f"{deleted_payments} ta pending Payment o'chirildi."
        ))
