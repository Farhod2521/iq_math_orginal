from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django_app.app_user.models import Student, Parent, Tutor

class Command(BaseCommand):
    help = "Status=False va ro'yxatdan o'tganiga 5 daqiqadan oshgan foydalanuvchilarni list qiladi."

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Agar berilsa, 5 daqiqadan kichiklarni ham ko\'rsatadi (ya\'ni barcha status=False).'
        )

    def handle(self, *args, **options):
        now = timezone.now()
        cutoff_time = now - timedelta(minutes=5)
        show_all = options.get('all', False)

        total = 0
        self.stdout.write(self.style.NOTICE("=== Studentlar ==="))
        if show_all:
            students = Student.objects.filter(status=False)
        else:
            students = Student.objects.filter(status=False, student_date__lt=cutoff_time)

        for s in students.select_related('user'):
            total += 1
            user_phone = s.user.phone if hasattr(s, 'user') else 'N/A'
            self.stdout.write(f"Student: id={s.id}, ism='{s.full_name}', phone={user_phone}, registered={s.student_date}")

        self.stdout.write(self.style.NOTICE("=== Ota-onalar ==="))
        if show_all:
            parents = Parent.objects.filter(status=False)
        else:
            parents = Parent.objects.filter(status=False, parent_date__lt=cutoff_time)

        for p in parents.select_related('user'):
            total += 1
            user_phone = p.user.phone if hasattr(p, 'user') else 'N/A'
            self.stdout.write(f"Parent: id={p.id}, ism='{p.full_name}', phone={user_phone}, registered={p.parent_date}")

        self.stdout.write(self.style.NOTICE("=== Tutorlar ==="))
        if show_all:
            tutors = Tutor.objects.filter(status=False)
        else:
            tutors = Tutor.objects.filter(status=False, tutor_date__lt=cutoff_time)

        for t in tutors.select_related('user'):
            total += 1
            user_phone = t.user.phone if hasattr(t, 'user') else 'N/A'
            self.stdout.write(f"Tutor: id={t.id}, ism='{t.full_name}', phone={user_phone}, registered={t.tutor_date}")

        self.stdout.write(self.style.SUCCESS(f"\nJami: {total} ta status=False foydalanuvchi topildi. (all={show_all})"))
        if not show_all:
            self.stdout.write(self.style.WARNING("Eslatma: Bu ro'yxat faqat 5 daqiqadan eski status=False yozuvlarni ko'rsatadi. Agar hammasini ko'rmoqchi bo'lsangiz, --all opsiyasini foydalaning."))
