from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_app.app_teacher.models import  Topic, Question, Chapter, CompositeSubQuestion, Choice
from django_app.app_user.models import  Subject, Subject_Category
from django_app.app_user.models import Student, Class
from .serializers import (
    SubjectSerializer, CustomQuestionSerializer, CheckAnswersSerializer, ChapterSerializer, 
    TopicSerializer
    )
import random
from django.db.models import Q
from collections import defaultdict
from bs4 import BeautifulSoup  # HTML teglarini tozalash uchun
from django.utils.html import strip_tags
from random import sample
from .models import Diagnost_Student
from rest_framework import status

import re
###################################   TIZIMGA KIRGAN O"QUVCHI BILIM DARAJASINI TEKSHIRISH #####################

class GenerateTestAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        student = Student.objects.get(user=request.user)
        if not student or not student.class_name:
            return Response({"message": "Foydalanuvchining sinfi topilmadi"}, status=400)


        current_class = student.class_name.classes.name
        
        try:
            prev_class = Class.objects.get(name=str(int(current_class) - 1))
            
        except (ValueError, Class.DoesNotExist):
            return Response({"message": "Quyi sinf topilmadi"}, status=400)
        subjects = Subject.objects.filter(
            classes__name=prev_class, category__name__iexact="Matematika"
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

        # Generate questions for each chapter
        for chapter in chapters:
            chapter_questions = Question.objects.filter(topic__chapter=chapter, level=level).distinct()
            count = min(per_chapter, chapter_questions.count())
            questions_list += sample(list(chapter_questions), count)

        # If there are not enough questions, add more from the same chapters
        if len(questions_list) < total_questions:
            remaining = total_questions - len(questions_list)
            extra_qs = Question.objects.filter(
                topic__chapter__in=chapters,
                level=level
            ).exclude(id__in=[q.id for q in questions_list])
            questions_list += sample(list(extra_qs), min(remaining, extra_qs.count()))

        # Serialize the data and filter out None values
        serializer = CustomQuestionSerializer(questions_list, many=True, context={'request': request})
        filtered_data = list(filter(None, serializer.data))  # Remove None values
        
        return Response(filtered_data)


class CheckAnswersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CheckAnswersSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"message": "Noto‘g‘ri formatdagi ma'lumotlar."}, status=400)

        try:
            student_instance = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({"message": "Student topilmadi"}, status=404)

        correct_answers = 0
        total_answers = 0
        question_details = []
        wrong_topics = {}  # Changed to a dictionary to track topics and their index
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
                if question.topic:
                    if question.topic.name_uz not in wrong_topics:
                        wrong_topics[question.topic.name_uz] = {
                            'index': len(wrong_topics) + 1,
                            'topic_name_ru': question.topic.name_ru,
                            'topic_name_uz': question.topic.name_uz
                        }

            question_details.append({
                "index": index,
                "question_id": question.id,
                "question_uz": question.question_text_uz,
                "question_ru": question.question_text_ru,
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
            correct_answers += is_correct

            if not is_correct:
                if question.topic:
                    if question.topic.name_uz not in wrong_topics:
                        wrong_topics[question.topic.name_uz] = {
                            'index': len(wrong_topics) + 1,
                            'topic_name_ru': question.topic.name_ru,
                            'topic_name_uz': question.topic.name_uz
                        }

            question_details.append({
                "index": index,
                "question_id": question.id,
                "question_uz": question.question_text_uz,
                "question_ru": question.question_text_ru,
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
            correct_answers += is_correct

            if not is_correct:
                if question.topic:
                    if question.topic.name_uz not in wrong_topics:
                        wrong_topics[question.topic.name_uz] = {
                            'index': len(wrong_topics) + 1,
                            'topic_name_ru': question.topic.name_ru,
                            'topic_name_uz': question.topic.name_uz
                        }

            question_details.append({
                "index": index,
                "question_id": question.id,
                "question_uz": question.question_text_uz,
                "question_ru": question.question_text_ru,
                "answer": is_correct
            })
            index += 1

        score = round((correct_answers / total_answers) * 100, 2) if total_answers else 0.0

        result_json = {
            "question": question_details,
            "Topic": [{"index": topic_info['index'],
                       "topic_name_uz": topic_info['topic_name_uz'],
                       "topic_name_ru": topic_info['topic_name_ru']}
                      for topic_info in wrong_topics.values()],
            "result": [{
                "total_answers": total_answers,
                "correct_answers": correct_answers,
                "score": score
            }]
        }

        Diagnost_Student.objects.create(
            student=student_instance,
            result=result_json
        )

        return Response(result_json)


class StudentSubjectListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # 1. Studentni user orqali olish
            student = Student.objects.get(user=request.user)
            student_class_name = student.class_name.id
            sub =  Subject.objects.filter(id=student_class_name)
            serializer = SubjectSerializer(sub, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Student.DoesNotExist:
            return Response({"detail": "Student topilmadi"}, status=status.HTTP_404_NOT_FOUND)


class ChapterListBySubjectAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, subject_id):
        try:
            subject = Subject.objects.get(id=subject_id)
            chapters = Chapter.objects.filter(subject=subject)
            serializer = ChapterSerializer(chapters, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Subject.DoesNotExist:
            return Response({"detail": "Subject topilmadi"}, status=status.HTTP_404_NOT_FOUND)

class TopicListByChapterAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, chapter_id):
        try:
            chapter = Chapter.objects.get(id=chapter_id)
            topics = Topic.objects.filter(chapter=chapter)
            serializer = TopicSerializer(topics, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Chapter.DoesNotExist:
            return Response({"detail": "Chapter topilmadi"}, status=status.HTTP_404_NOT_FOUND)
        
class QuestionListByTopicAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, topic_id):
        level = request.query_params.get('level', None) 
        
        try:
            topic = Topic.objects.get(id=topic_id)
            if level is not None:
                questions = Question.objects.filter(topic=topic, level=level)
            else:
                questions = Question.objects.filter(topic=topic)
            serializer = CustomQuestionSerializer(questions, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Topic.DoesNotExist:
            return Response({"detail": "Mavzu topilmadi"}, status=status.HTTP_404_NOT_FOUND)