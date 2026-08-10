from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django_app.app_user.models import Class, Subject
from django_app.app_teacher.models import Chapter, Topic
from django_app.app_student.models import TopicProgress, StudentScoreLog
from django_app.app_student.helper_next_topic import get_next_topic_for_student


def _class_sort_key(class_obj):
    # Raqamli sinflar (1, 2, ... 11) sonli tartibda, raqamsiz nomlar (masalan "Testlar") oxirida.
    return (0, int(class_obj.name)) if class_obj.name.isdigit() else (1, class_obj.name)


class StudentHomeDashboardAPIView(APIView):
    """
    Bosh sahifa uchun: mavjud sinflar ro'yxati, davom etilayotgan mavzu va
    tanlangan sinf bo'yicha statistika bitta so'rovda qaytariladi.

    Query param: ?class_id=<Class.id> — berilsa, o'sha sinfning fani bo'yicha
    continue_learning/stats hisoblanadi (bo'lmasa, o'quvchining o'z sinfi ishlatiladi).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not hasattr(request.user, "student_profile"):
            return Response({"error": "Faqat talaba uchun"}, status=403)

        student = request.user.student_profile

        classes_qs = Class.objects.filter(
            subjects__active=True, subjects__chapters__topics__isnull=False
        ).distinct()
        classes = [{"id": c.id, "name": c.name} for c in sorted(classes_qs, key=_class_sort_key)]

        requested_class_id = request.query_params.get("class_id")
        if requested_class_id:
            subject = (
                Subject.objects.filter(classes_id=requested_class_id, active=True).order_by("order").first()
            )
            scoped_to_requested_class = True
        else:
            subject = student.class_name  # o'quvchining o'z sinfi/fani
            scoped_to_requested_class = False

        continue_learning = None
        next_topic_info = (
            get_next_topic_for_student(student, subject=subject if scoped_to_requested_class else None)
            if subject
            else None
        )
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
