
import random
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_app.app_student.models import TopicProgress
from django_app.app_teacher.models import Question

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

        topic_ids = TopicProgress.objects.filter(
            user=student,
            score__gt=0
        ).values_list("topic_id", flat=True)

        if not topic_ids:
            return Response(
                {"detail": "Score 60 dan yuqori mavzular topilmadi"},
                status=404
            )

        topic_id = random.choice(list(topic_ids))

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
            "topic_name": question.topic.name,
            "question_text": question.question_text,
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
