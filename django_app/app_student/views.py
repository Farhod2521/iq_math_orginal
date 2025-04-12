from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_app.app_teacher.models import Subject, Topic, Question, Chapter, Subject_Category, CompositeSubQuestion, Choice
from django_app.app_user.models import Student, Class
from .serializers import (
    SubjectSerializer, CustomQuestionSerializer, CheckAnswersSerializer
    )
import random
from django.db.models import Q
from collections import defaultdict
from bs4 import BeautifulSoup  # HTML teglarini tozalash uchun
from django.utils.html import strip_tags
from random import sample

from rest_framework import status
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
        student = getattr(request.user, 'student_profile', None)
        if not student or not student.class_name:
            return Response({"message": "Foydalanuvchining sinfi topilmadi"}, status=400)

        current_class = student.class_name
        try:
            prev_class = Class.objects.get(name=str(int(current_class.name) - 1))
        except (ValueError, Class.DoesNotExist):
            return Response({"message": "Quyi sinf topilmadi"}, status=400)

        subjects = Subject.objects.filter(
            classes=prev_class, category__name__iexact="Matematika"
        )
        if not subjects.exists():
            return Response({"message": "Matematika fani topilmadi"}, status=400)

        subject = subjects.first()
        chapters = subject.chapters.all()
        level = request.data.get("level")

        try:
            level = int(level)
        except (TypeError, ValueError):
            return Response({"message": "Level noto‘g‘ri formatda"}, status=400)

        total_questions = 30
        per_chapter = total_questions // chapters.count() if chapters.exists() else 0
        questions_list = []

        for chapter in chapters:
            chapter_questions = Question.objects.filter(topic__chapter=chapter, level=level).distinct()
            count = min(per_chapter, chapter_questions.count())
            questions_list += sample(list(chapter_questions), count)

        if len(questions_list) < total_questions:
            remaining = total_questions - len(questions_list)
            extra_qs = Question.objects.filter(
                topic__chapter__in=chapters,
                level=level
            ).exclude(id__in=[q.id for q in questions_list])
            questions_list += sample(list(extra_qs), min(remaining, extra_qs.count()))

        # Serialize va None bo‘lganlarni (composite with no sub) chiqarib tashlash
        serializer = CustomQuestionSerializer(questions_list, many=True, context={'request': request})
        filtered_data = list(filter(None, serializer.data))  # None bo‘lganlarini olib tashlash
        return Response(filtered_data)


class CheckAnswersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CheckAnswersSerializer(data=request.data, many=True)

        if serializer.is_valid():
            # If validation passes, check all answers
            return Response({"message": "Javoblar to‘g‘ri tekshirildi."}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)