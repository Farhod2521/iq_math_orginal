from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Book


@receiver(post_save, sender=Book)
def book_created_notification(sender, instance, created, **kwargs):
    if created and instance.status == 'active':
        from django_app.app_user.notification_service import send_push_to_all_students
        send_push_to_all_students(
            title="Yangi kitob qo'shildi!",
            body=instance.name,
            data={"type": "new_book", "book_id": str(instance.pk)},
        )
