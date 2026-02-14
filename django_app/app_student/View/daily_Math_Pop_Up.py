
import random
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_app.app_student.models import TopicProgress
from django_app.app_teacher.models import Question, Topic

from django_app.app_user.models import Student

from rest_framework import status


class QuickMathQuestionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 1️⃣ Student profilini olish
        student = getattr(request.user, "student_profile", None)
        if not student:
            return Response(
                {"detail": "Student profili topilmadi"},
                status=status.HTTP_404_NOT_FOUND
            )

        # 2️⃣ Oldin ishlangan topiclarni olish
        topic_ids = TopicProgress.objects.filter(
            user=student,
            score__gt=0
        ).values_list("topic_id", flat=True)

        # 3️⃣ Savollarni shakllantirish
        questions = Question.objects.filter(
            question_type="text"
        )

        # Agar ishlangan topiclar bo‘lsa → o‘shalardan
        if topic_ids.exists():
            questions = questions.filter(topic_id__in=topic_ids)
        else:
            # Aks holda student fanidan
            subject = student.class_name
            if not subject:
                return Response(
                    {"detail": "Student fan tanlamagan"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            questions = questions.filter(
                topic__chapter__subject=subject
            )

        # 4️⃣ Agar savol topilmasa
        if not questions.exists():
            return Response(
                {"detail": "Mos text savol topilmadi"},
                status=status.HTTP_404_NOT_FOUND
            )

        # 5️⃣ Random savol tanlash
        question = random.choice(list(questions))

        return Response({
            "question_id": question.id,
            "topic_id": question.topic.id,
            "topic_name_uz": question.topic.name_uz,
            "topic_name_ru": question.topic.name_ru,
            "question_text_uz": question.question_text_uz,
            "question_text_ru": question.question_text_ru,
            "level": question.level
        }, status=status.HTTP_200_OK)




class SubmitQuickMathAnswerAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        question_id = request.data.get("question_id")
        user_answer = request.data.get("answer")

        if not question_id or not user_answer:
            return Response({
                "detail": "question_id va answer majburiy"
            }, status=400)

        try:
            question = Question.objects.get(
                id=question_id,
                question_type="text"
            )
        except Question.DoesNotExist:
            return Response({
                "detail": "Savol topilmadi"
            }, status=404)

        # Tozalab solishtirish
        correct_answer = question.correct_text_answer.strip().lower()
        user_answer = user_answer.strip().lower()

        is_correct = correct_answer == user_answer

        return Response({
            "is_correct": is_correct,
            "message": "Excellent! 🎉" if is_correct else "Try again 😔",
            "emoji": "😊" if is_correct else "😢"
        })
