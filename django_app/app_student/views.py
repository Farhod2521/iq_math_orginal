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
from .models import Diagnost_Student
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



# class CheckAnswersAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         serializer = CheckAnswersSerializer(data=request.data)

#         if not serializer.is_valid():
#             return Response({"message": "Noto‘g‘ri formatdagi ma'lumotlar."}, status=400)

#         correct_answers = 0
#         total_answers = 0

#         # Check Text Answers
#         if serializer.validated_data.get('text_answers'):
#             text_answers = serializer.validated_data['text_answers']
#             for answer in text_answers:
#                 total_answers += 1
#                 question = Question.objects.filter(id=answer['question_id'], question_type="text").first()
#                 if question:
#                     if question.correct_text_answer == answer['answer']:
#                         correct_answers += 1

#         # Check Choice Answers
#         if serializer.validated_data.get('choice_answers'):
#             choice_answers = serializer.validated_data['choice_answers']
#             for answer in choice_answers:
#                 total_answers += 1
#                 question = Question.objects.filter(id=answer['question_id'], question_type="choice").first()
#                 if question:
#                     correct_choices = Choice.objects.filter(question=question, is_correct=True).values_list('id', flat=True)
#                     if set(answer['choices']) == set(correct_choices):
#                         correct_answers += 1

#         # Check Composite Answers
#         if serializer.validated_data.get('composite_answers'):
#             composite_answers = serializer.validated_data['composite_answers']
#             for answer in composite_answers:
#                 total_answers += 1
#                 question = Question.objects.filter(id=answer['question_id'], question_type="composite").first()
#                 if question:
#                     correct_answers_count = 0
#                     for sub_answer, sub_question in zip(answer['answers'], question.sub_questions.all()):
#                         if sub_answer == sub_question.correct_answer:
#                             correct_answers_count += 1
#                     if correct_answers_count == question.sub_questions.count():
#                         correct_answers += 1

#         # Return the response with score
#         return Response({
#             "total_answers": total_answers,
#             "correct_answers": correct_answers,
#             "score": (correct_answers / total_answers) * 100 if total_answers > 0 else 0
#         })


class CheckAnswersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CheckAnswersSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"message": "Noto‘g‘ri formatdagi ma'lumotlar."}, status=400)

        student = request.user.student  # Assuming there's a one-to-one user-student relation

        correct_answers = 0
        total_answers = 0
        question_details = []
        wrong_topics = set()
        index = 1

        # --- TEXT ANSWERS ---
        for answer in serializer.validated_data.get('text_answers', []):
            question = Question.objects.filter(id=answer['question_id'], question_type='text').first()
            if not question:
                continue

            is_correct = (question.correct_text_answer == answer['answer'])
            total_answers += 1
            if is_correct:
                correct_answers += 1
            else:
                wrong_topics.add(question.topic.name)

            question_details.append({
                "index": index,
                "question_id": question.id,
                "question_uz": question.question_text,
                "question_ru": "",  # Add if multilingual support exists
                "answer": is_correct
            })
            index += 1

        # --- CHOICE ANSWERS ---
        for answer in serializer.validated_data.get('choice_answers', []):
            question = Question.objects.filter(id=answer['question_id'], question_type='choice').first()
            if not question:
                continue

            correct_choices = set(Choice.objects.filter(question=question, is_correct=True).values_list('id', flat=True))
            selected_choices = set(answer['choices'])

            is_correct = (correct_choices == selected_choices)
            total_answers += 1
            if is_correct:
                correct_answers += 1
            else:
                wrong_topics.add(question.topic.name)

            question_details.append({
                "index": index,
                "question_id": question.id,
                "question_uz": question.question_text,
                "question_ru": "",
                "answer": is_correct
            })
            index += 1

        # --- COMPOSITE ANSWERS ---
        for answer in serializer.validated_data.get('composite_answers', []):
            question = Question.objects.filter(id=answer['question_id'], question_type='composite').first()
            if not question:
                continue

            correct_subs = question.sub_questions.all()
            is_correct = True
            for sub_answer, sub_question in zip(answer['answers'], correct_subs):
                if sub_answer != sub_question.correct_answer:
                    is_correct = False
                    break

            total_answers += 1
            if is_correct:
                correct_answers += 1
            else:
                wrong_topics.add(question.topic.name)

            question_details.append({
                "index": index,
                "question_id": question.id,
                "question_uz": question.question_text,
                "question_ru": "",
                "answer": is_correct
            })
            index += 1

        # Calculate score
        score = round((correct_answers / total_answers) * 100, 2) if total_answers else 0.0

        # Prepare result JSON
        result_json = {
            "question": question_details,
            "Topic": [{"topic_name": name} for name in wrong_topics],
            "result": [{
                "total_answers": total_answers,
                "correct_answers": correct_answers,
                "score": score
            }]
        }

        # Save to Diagnost_Student
        Diagnost_Student.objects.create(
            student=student,
            result=result_json
        )

        # Return score response
        return Response({
            "total_answers": total_answers,
            "correct_answers": correct_answers,
            "score": score
        })