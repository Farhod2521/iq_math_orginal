
import random
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_app.app_student.models import TopicProgress
from django_app.app_teacher.models import Question, Topic

from django_app.app_user.models import Student




class QuickMathQuestionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            student = request.user.student_profile
        except Student.DoesNotExist:
            return Response(
                {"detail": "Student profili topilmadi"},
                status=404
            )

        # 1️⃣ Oldin ishlangan mavzularni tekshiramiz
        topic_ids = TopicProgress.objects.filter(
            user=student,
            score__gt=0
        ).values_list("topic_id", flat=True)

        # 2️⃣ Agar ishlangan mavzular bo‘lsa
        if topic_ids.exists():
            topic_id = random.choice(list(topic_ids))
            topics = Topic.objects.filter(id=topic_id)

        # 3️⃣ Aks holda: student tanlagan fanidan olamiz
        else:
            subject = student.class_name  # bu Subject

            if not subject:
                return Response(
                    {"detail": "Student fan tanlamagan"},
                    status=404
                )

            topics = Topic.objects.filter(
                chapter__subject=subject
            )

            if not topics.exists():
                return Response(
                    {"detail": "Bu fan uchun mavzular topilmadi"},
                    status=404
                )

            topic = random.choice(list(topics))
            topic_id = topic.id

        # 4️⃣ O‘sha topic bo‘yicha savollar
        questions = Question.objects.filter(
            topic_id=topic_id,
            question_type="text"
        )

        if not questions.exists():
            return Response(
                {"detail": "Text savollar topilmadi"},
                status=404
            )

        question = random.choice(list(questions))

        return Response({
            "question_id": question.id,
            "topic_id": question.topic.id,
            "topic_name_uz": question.topic.name_uz,
            "topic_name_ru": question.topic.name_ru,
            "question_text_uz": question.question_text_uz,
            "question_text_ru": question.question_text_ru,
            "level": question.level
        })




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
