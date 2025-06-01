from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django_app.app_teacher.models import  UnsolvedQuestionReport, Question
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

class UnsolvedQuestionCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        question_id = request.data.get("question_id")
        message = request.data.get("message", "")

        # request.user orqali student profilini aniqlash
        try:
            student = request.user.student_profile  # yoki request.user.student bo'lishi mumkin, tekshiring
        except AttributeError:
            return Response({"error": "Siz student emassiz"}, status=status.HTTP_403_FORBIDDEN)

        try:
            question = Question.objects.get(id=question_id)
        except Question.DoesNotExist:
            return Response({"error": "Savol topilmadi"}, status=status.HTTP_404_NOT_FOUND)

        # Takroran yuborishni oldini olish
        if UnsolvedQuestionReport.objects.filter(question=question, student=student).exists():
            return Response({"error": "Bu savol allaqachon yuborilgan"}, status=status.HTTP_400_BAD_REQUEST)

        # Barcha o‘qituvchilarni olish - TO‘G‘RILANDI:
        try:
            teachers = question.topic.chapter.subject.teachers.all()
        except AttributeError:
            return Response({"error": "Savolga tegishli fan uchun o‘qituvchilar topilmadi"}, status=status.HTTP_400_BAD_REQUEST)

        report = UnsolvedQuestionReport.objects.create(
            question=question,
            student=student,
            message=message,
            status="pending",
            created_at=timezone.now()
        )
        report.teachers.set(teachers)
        report.save()

        return Response({"success": "Misol yuborildi"}, status=status.HTTP_201_CREATED)
