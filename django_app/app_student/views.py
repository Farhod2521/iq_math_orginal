from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_app.app_teacher.models import Subject, Topic, Question, Chapter
from django_app.app_user.models import Student, Class
from .serializers import SubjectSerializer
import random
from django.db.models import Q



class MySubjectsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = Student.objects.filter(user=request.user).first()
        if not student or not student.class_name:
            return Response({"message": "Sinfga tegishli emas yoki profil topilmadi"}, status=404)

        subjects = Subject.objects.filter(classes=student.class_name)
        serializer = SubjectSerializer(subjects, many=True)

        return Response(serializer.data)
    

###################################   TIZIMGA KIRGAN O"QUVCHI BILIM DARAJASINI TEKSHIRISH #####################

class GenerateTestAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = request.user.student_profile  
        current_class = student.class_name

        if not current_class:
            return Response({"message": "Sinf topilmadi"}, status=400)

        lower_class = Class.objects.filter(id=current_class.id - 1).first()
        if not lower_class:
            return Response({"message": "Past sinf mavjud emas"}, status=400)

        subjects = Subject.objects.filter(classes=lower_class)
        questions = []

        for subject in subjects:
            chapters = Chapter.objects.filter(subject=subject)
            chapter_count = chapters.count()

            if chapter_count == 0:
                continue

            per_chapter = max(1, 30 // chapter_count)  # Har bir bobga ajratiladigan savollar soni

            for chapter in chapters:
                chapter_questions = list(
                    Question.objects.filter(topic__chapter=chapter, level=1)
                )
                if chapter_questions:
                    selected_questions = random.sample(
                        chapter_questions, min(per_chapter, len(chapter_questions))
                    )
                    questions.extend(selected_questions)

        questions = random.sample(questions, min(30, len(questions)))

        data = [
            {"id": q.id, "text": q.question_text, "topic": q.topic.name}
            for q in questions
        ]

        return Response({"questions": data})