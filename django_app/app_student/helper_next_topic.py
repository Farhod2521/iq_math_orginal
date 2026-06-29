from django_app.app_teacher.models import Topic, Chapter
from django_app.app_student.models import TopicProgress


def get_next_topic_for_student(student):
    """
    Studentning keyingi o'rganishi kerak bo'lgan mavzusini qaytaradi.
    Returns: dict yoki None
    """
    progresses = (
        TopicProgress.objects
        .filter(user=student)
        .select_related("topic", "topic__chapter", "topic__chapter__subject")
        .order_by('-completed_at', '-id')
    )

    if progresses.exists():
        last_topic = progresses.first().topic
        subject = last_topic.chapter.subject
        chapter_topics = list(Topic.objects.filter(chapter=last_topic.chapter).order_by('order'))

        try:
            current_index = chapter_topics.index(last_topic)
            if current_index == len(chapter_topics) - 1:
                next_chapter = Chapter.objects.filter(
                    subject=subject,
                    order__gt=last_topic.chapter.order
                ).order_by('order').first()
                next_topic = Topic.objects.filter(chapter=next_chapter).order_by('order').first() if next_chapter else None
            else:
                next_topic = chapter_topics[current_index + 1]
        except ValueError:
            next_topic = None

        if next_topic:
            return _build_response(next_topic, subject)

    if student.class_name:
        subject = student.class_name
        first_chapter = Chapter.objects.filter(subject=subject).order_by('order').first()
        if first_chapter:
            first_topic = Topic.objects.filter(chapter=first_chapter).order_by('order').first()
            if first_topic:
                return _build_response(first_topic, subject)

    return None


def _build_response(topic, subject):
    return {
        "topic_id": topic.id,
        "subject_name_uz": subject.name_uz,
        "subject_name_ru": subject.name_ru,
        "topic_name_uz": topic.name_uz,
        "topic_name_ru": topic.name_ru,
    }
