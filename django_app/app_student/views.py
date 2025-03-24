from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_app.app_teacher.models import Subject, Topic, Question, Chapter
from django_app.app_user.models import Student, Class
from .serializers import SubjectSerializer
import random
from django.db.models import Q
from collections import defaultdict
from bs4 import BeautifulSoup  # HTML teglarini tozalash uchun
from django.utils.html import strip_tags

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

    def post(self, request):
        student = request.user.student_profile  
        current_class = student.class_name
        level = request.data.get("level")  # POST so‘rov orqali level qabul qilinadi

        if not current_class:
            return Response({"message": "Sinf topilmadi"}, status=400)

        if level is None:
            return Response({"message": "Level ko‘rsatilmagan"}, status=400)

        try:
            level = int(level)  # Levelni int formatga o‘tkazamiz
        except ValueError:
            return Response({"message": "Level noto‘g‘ri formatda"}, status=400)

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
                    Question.objects.filter(topic__chapter=chapter, level=level)
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
    

class CheckAnswersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_answers = request.data.get("answers", {})  # Foydalanuvchidan kelgan javoblar

        if not user_answers:
            return Response({"message": "Javoblar taqdim etilmagan"}, status=400)

        correct_count = 0
        incorrect_count = 0
        incorrect_topics = defaultdict(set)

        for question_id, user_answer in user_answers.items():
            try:
                question = Question.objects.get(id=question_id)
            except Question.DoesNotExist:
                continue  # Noto‘g‘ri yoki mavjud bo‘lmagan savollarni e'tiborsiz qoldiramiz

            # HTML teglarini olib tashlash
            correct_answer_text = strip_tags(question.correct_answer).strip().lower()
            user_answer_text = strip_tags(user_answer).strip().lower()

            if correct_answer_text == user_answer_text:
                correct_count += 1
            else:
                incorrect_count += 1
                incorrect_topics[question.topic.chapter.name].add(question.topic.name)

        # Xato qilingan mavzularni tuzib chiqamiz
        recommended_topics = [
            {"chapter": chapter, "topics": list(topics)}
            for chapter, topics in incorrect_topics.items()
        ]

        return Response({
            "correct": correct_count,
            "incorrect": incorrect_count,
            "recommendations": recommended_topics
        })