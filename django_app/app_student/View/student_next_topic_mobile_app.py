from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django_app.app_student.helper_next_topic import get_next_topic_for_student
from django_app.app_student.models import TopicProgress






class StudentNextTopicAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if not hasattr(user, 'student_profile'):
            return Response({"detail": "Faqat o'quvchilar uchun."}, status=status.HTTP_403_FORBIDDEN)

        result = get_next_topic_for_student(user.student_profile)
        if result:
            return Response(result, status=status.HTTP_200_OK)
        return Response({"detail": "Hozircha hech qanday mavzu mavjud emas."}, status=status.HTTP_204_NO_CONTENT)



class StudentLastProgressAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # ✅ Faqat student kirishi mumkin
        if not hasattr(user, 'student_profile'):
            return Response(
                {"detail": "Faqat o'quvchilar uchun."},
                status=status.HTTP_403_FORBIDDEN
            )

        student = user.student_profile

        # 🔍 Oxirgi ishlangan 5 ta mavzu
        progresses = (
            TopicProgress.objects
            .filter(user=student)
            .select_related(
                'topic',
                'topic__chapter',
                'topic__chapter__subject'
            )
            .order_by('-completed_at')[:5]
        )

        # 🆕 Agar hali hech narsa ishlanmagan bo'lsa — bo'sh list
        if not progresses.exists():
            return Response([], status=status.HTTP_200_OK)

        data = []

        for progress in progresses:
            topic = progress.topic
            chapter = topic.chapter
            subject = chapter.subject
            class_name =  chapter.subject.classes.name

            data.append({
                "class_name_uz": f"{class_name}-sinf",
                "class_name_ru": f"{class_name}-класс",
    
                "subject_name_uz": subject.name_uz,
                "subject_name_ru": subject.name_ru,
                "chapter_name_uz": chapter.name_uz,
                "chapter_name_ru": chapter.name_ru,
                "chapter_id":chapter.id, 
                "topic_name_uz": topic.name_uz,
                "topic_name_ru": topic.name_ru,
                "topic_id":topic.id,
                "score": round(progress.score, 1),
                "completed_at": (
                    progress.completed_at.strftime("%d/%m/%Y %H:%M")
                    if progress.completed_at else None
                )
            })

        return Response(data, status=status.HTTP_200_OK)
