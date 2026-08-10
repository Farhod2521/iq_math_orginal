from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django_app.app_user.models import Class
from django_app.app_teacher.models import Chapter, Topic
from django_app.app_student.models import TopicProgress, StudentScoreLog
from django_app.app_student.helper_next_topic import get_next_topic_for_student


class StudentHomeDashboardAPIView(APIView):
    """
    Bosh sahifa uchun: mavjud sinflar ro'yxati, davom etilayotgan mavzu va
    o'quvchining o'z sinfi bo'yicha statistikasi bitta so'rovda qaytariladi.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not hasattr(request.user, "student_profile"):
            return Response({"error": "Faqat talaba uchun"}, status=403)

        student = request.user.student_profile
        subject = student.class_name  # Subject instance (o'quvchining o'z sinfi/fani)

        classes_qs = (
            Class.objects.filter(subjects__active=True, subjects__chapters__topics__isnull=False)
            .distinct()
            .order_by("name")
        )
        classes = [{"id": c.id, "name": c.name} for c in classes_qs]

        continue_learning = None
        next_topic_info = get_next_topic_for_student(student)
        if next_topic_info:
            topic = Topic.objects.select_related("chapter", "chapter__subject").get(id=next_topic_info["topic_id"])
            chapter = topic.chapter
            chapter_order = Chapter.objects.filter(subject=chapter.subject, order__lte=chapter.order).count()
            topics_total_in_chapter = Topic.objects.filter(chapter=chapter).count()
            topics_done_in_chapter = TopicProgress.objects.filter(
                user=student, topic__chapter=chapter, score__gte=80
            ).count()
            percent = (
                round((topics_done_in_chapter / topics_total_in_chapter) * 100) if topics_total_in_chapter else 0
            )

            continue_learning = {
                **next_topic_info,
                "chapter_order": chapter_order,
                "topics_done_in_chapter": topics_done_in_chapter,
                "topics_total_in_chapter": topics_total_in_chapter,
                "percent": percent,
            }

        stats = {
            "chapter_count": 0,
            "topic_count": 0,
            "completed_topic_count": 0,
            "average_score_percent": 0,
            "solved_questions_count": 0,
        }
        if subject:
            topic_progresses = TopicProgress.objects.filter(user=student, topic__chapter__subject=subject)
            attempted_scores = list(topic_progresses.values_list("score", flat=True))

            stats = {
                "chapter_count": Chapter.objects.filter(subject=subject).count(),
                "topic_count": Topic.objects.filter(chapter__subject=subject).count(),
                "completed_topic_count": topic_progresses.filter(score__gte=80).count(),
                "average_score_percent": (
                    round(sum(attempted_scores) / len(attempted_scores)) if attempted_scores else 0
                ),
                "solved_questions_count": StudentScoreLog.objects.filter(
                    student_score__student=student, question__topic__chapter__subject=subject
                ).count(),
            }

        return Response(
            {
                "classes": classes,
                "current_class_id": subject.classes_id if subject else None,
                "current_class_name": subject.classes.name if subject and subject.classes else None,
                "continue_learning": continue_learning,
                "stats": stats,
            },
            status=200,
        )
