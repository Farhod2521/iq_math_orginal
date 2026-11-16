"""
Demo darslar: obunasi (pullik yoki tekin sinov) bo'lmagan o'quvchiga har bir sinfda
dastlabki DEMO_TOPICS_PER_CLASS ta mavzu bepul ochiladi.

Tartib: fan (order) -> bob (order) -> mavzu (order). Ya'ni sinfning birinchi fanidagi
birinchi ikki mavzu bepul bo'ladi.
"""
from django.utils.timezone import now

from django_app.app_payments.models import Subscription
from django_app.app_teacher.models import Topic

DEMO_TOPICS_PER_CLASS = 2


def student_has_full_access(student):
    """Pullik obuna yoki tekin sinov muddati hozir amalda bo'lsa — True."""
    if student is None:
        return False
    try:
        sub = student.subscription
    except Subscription.DoesNotExist:
        return False
    current = now()
    return bool(sub.start_date and sub.end_date and sub.start_date <= current <= sub.end_date)


def demo_topic_ids_for_class(class_id):
    """Sinfdagi bepul demo mavzular ID lari (set)."""
    if not class_id:
        return set()
    ids = (
        Topic.objects.filter(
            chapter__subject__classes_id=class_id,
            chapter__subject__active=True,
        )
        .order_by(
            'chapter__subject__order', 'chapter__subject_id',
            'chapter__order', 'chapter_id',
            'order', 'id',
        )
        .values_list('id', flat=True)[:DEMO_TOPICS_PER_CLASS]
    )
    return set(ids)


def demo_topic_ids_for_topic(topic):
    """Mavzu qaysi sinfga tegishli bo'lsa — o'sha sinfning demo mavzulari."""
    subject = getattr(getattr(topic, 'chapter', None), 'subject', None)
    return demo_topic_ids_for_class(getattr(subject, 'classes_id', None))


def is_topic_available(user, topic):
    """Talaba shu mavzuni ochishi mumkinmi (obuna yoki demo)."""
    if getattr(user, 'role', None) != 'student':
        return True
    student = getattr(user, 'student_profile', None)
    if student_has_full_access(student):
        return True
    return topic.id in demo_topic_ids_for_topic(topic)
