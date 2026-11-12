"""Liga ballari mavjud tizimdan olinadi: kirish va fanlarni ishlash kodi o'zgarmaydi."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from django_app.app_student.models import StudentScoreLog
from django_app.app_user.models import StudentLoginHistory

from . import services


@receiver(post_save, sender=StudentLoginHistory)
def award_daily_login(sender, instance, created, **kwargs):
    if created:
        services.award_daily_login(instance.student_id)


@receiver(post_save, sender=StudentScoreLog)
def award_subject_work(sender, instance, created, **kwargs):
    # Gol faqat tanga berilgan savol uchun: 1 tanga = 1 gol. Tanga kunlik chegarali (admin sozlamasi,
    # masalan 15), shuning uchun fanlardan gol ham kuniga shuncha. Chegara to'lgach ball beriladi — gol yo'q.
    if created and instance.award_type == 'coin':
        services.award_subject_work(instance.student_score.student_id, instance.id)
