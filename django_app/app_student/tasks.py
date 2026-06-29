from celery import shared_task
from django_app.app_user.models import User
from django_app.app_user.notification_service import send_push_notification
from django_app.app_student.helper_next_topic import get_next_topic_for_student


@shared_task(name="send_daily_topic_notifications")
def send_daily_topic_notifications():
    students = (
        User.objects
        .filter(role='student', fcm_token__isnull=False)
        .exclude(fcm_token='')
        .select_related('student_profile')
    )

    sent = 0
    skipped = 0

    for user in students:
        student = getattr(user, 'student_profile', None)
        if not student:
            skipped += 1
            continue

        next_topic = get_next_topic_for_student(student)
        if not next_topic:
            skipped += 1
            continue

        title = f"Bugungi maqsad: {next_topic['subject_name_uz']}"
        body = next_topic['topic_name_uz']

        success = send_push_notification(
            fcm_token=user.fcm_token,
            title=title,
            body=body,
            data={
                "type": "daily_topic",
                "topic_id": str(next_topic['topic_id']),
                "subject_name_uz": next_topic['subject_name_uz'],
                "subject_name_ru": next_topic['subject_name_ru'],
            }
        )

        if success:
            sent += 1
        else:
            skipped += 1

    return f"Yuborildi: {sent}, o'tkazib yuborildi: {skipped}"
