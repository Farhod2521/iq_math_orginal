from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django_app.app_user.models import Student, Parent, Tutor

class Command(BaseCommand):
    help = "03:00 da status=False bo'lgan eski foydalanuvchilarni (5 daqiqadan eski) o'chiradi."

    def handle(self, *args, **options):
        now = timezone.now()
        cutoff_time = now - timedelta(minutes=5)
        deleted_count = 0

        # 1️⃣ Studentlar
        students = Student.objects.filter(status=False, student_date__lt=cutoff_time)
        for s in students:
            s.user.delete()
            deleted_count += 1

        # 2️⃣ Ota-onalar
        parents = Parent.objects.filter(status=False, parent_date__lt=cutoff_time)
        for p in parents:
            p.user.delete()
            deleted_count += 1

        # 3️⃣ Tutorlar
        tutors = Tutor.objects.filter(status=False, tutor_date__lt=cutoff_time)
        for t in tutors:
            t.user.delete()
            deleted_count += 1

        self.stdout.write(self.style.SUCCESS(f"{deleted_count} ta foydalanuvchi o'chirildi."))
