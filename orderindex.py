import os
import django

# Django sozlamalarini ulaymiz
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

# Endi modellaringni import qilamiz
from django_app.app_teacher.models import Topic, Chapter
from django_app.app_user.models import Subject

def update_chapter_orders():
    subjects = Subject.objects.all().order_by('id')  # yoki 'name'
    for index, subject in enumerate(subjects, start=1):
        subject.order = index
        subject.save()
        print(f"{subject.name} -> order: {index}")

if __name__ == "__main__":
    update_chapter_orders()
