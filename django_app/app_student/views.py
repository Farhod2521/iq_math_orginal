from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_app.app_teacher.models import Subject, Topic, Question, Chapter, Subject_Category
from django_app.app_user.models import Student, Class
from .serializers import SubjectSerializer, QuestionSerializer
import random
from django.db.models import Q
from collections import defaultdict
from bs4 import BeautifulSoup  # HTML teglarini tozalash uchun
from django.utils.html import strip_tags
from random import sample
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
        # Step 1: Foydalanuvchi va sinfini tekshiramiz
        student = getattr(request.user, 'student_profile', None)
        if not student or not student.class_name:
            return Response({"message": "Foydalanuvchining sinfi topilmadi"}, status=400)

        # Step 2: 1 pog‘ona past sinfni aniqlaymiz
        current_class = student.class_name
        try:
            prev_class = Class.objects.get(name=str(int(current_class.name) - 1))
        except (ValueError, Class.DoesNotExist):
            return Response({"message": "Quyi sinf topilmadi"}, status=400)

        # Step 3: Matematika fani aniqlanadi
        subjects = Subject.objects.filter(
            classes=prev_class, category__name__iexact="Matematika"
        )
        print(subjects)
        if not subjects.exists():
            return Response({"message": "Matematika fani topilmadi"}, status=400)

        subject = subjects.first()  # faqat bittasini olamiz

        # Step 4: Fan boblari va savollar
        chapters = subject.chapters.all()
        
        chapter_count = chapters.count()
        level = request.data.get("level")
        print(chapters)
        if not level:
            return Response({"message": "Level yuboring"}, status=400)

        try:
            level = int(level)
        except ValueError:
            return Response({"message": "Level noto‘g‘ri formatda"}, status=400)

        total_questions = 30
        per_chapter = total_questions // chapter_count if chapter_count else 0
        questions_list = []


        for chapter in chapters:
            chapter_questions = Question.objects.filter(
                topic__chapter=chapter,
                level=level
            ).distinct()
            

            if chapter_questions.exists():
                count = min(per_chapter, chapter_questions.count())
                questions_list += sample(list(chapter_questions), count)

        # Agar yetarli bo‘lmasa, boshqa boblardan to‘ldiramiz
        if len(questions_list) < total_questions:
            remaining = total_questions - len(questions_list)
            all_other_questions = Question.objects.filter(
                topic__chapter__in=chapters,
                level=level
            ).exclude(id__in=[q.id for q in questions_list])
            if all_other_questions.exists():
                questions_list += sample(list(all_other_questions), min(remaining, all_other_questions.count()))

        serializer = QuestionSerializer(questions_list, many=True, context={'request': request})
        return Response(serializer.data)


class CheckAnswersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_answers = request.data.get("answers", {})
        if not user_answers:
            return Response({"message": "Javoblar taqdim etilmagan"}, status=400)

        question_ids = [int(qid) for qid in user_answers.keys() if str(qid).isdigit()]
        questions = Question.objects.filter(id__in=question_ids).select_related("topic__chapter")

        correct_count = 0
        incorrect_count = 0
        incorrect_topics = defaultdict(set)

        for question in questions:
            user_answer = user_answers.get(str(question.id), "")
            correct_answer = strip_tags(question.correct_answer or "").strip().lower()
            given_answer = strip_tags(user_answer).strip().lower()

            if correct_answer == given_answer:
                correct_count += 1
            else:
                incorrect_count += 1
                chapter_name = question.topic.chapter.name
                topic_name = question.topic.name
                incorrect_topics[chapter_name].add(topic_name)

        # Xato qilingan bo‘lim va mavzular ro‘yxatini tayyorlaymiz
        recommendations = [
            {"chapter": chapter, "topics": sorted(list(topics))}
            for chapter, topics in incorrect_topics.items()
        ]

        return Response({
            "correct": correct_count,
            "incorrect": incorrect_count,
            "recommendations": recommendations
        })
