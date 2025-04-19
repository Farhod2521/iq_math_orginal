from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_app.app_teacher.models import  Topic, Question, Chapter, CompositeSubQuestion, Choice
from django_app.app_user.models import  Subject, Subject_Category
from django_app.app_user.models import Student, Class
from .serializers import (
    SubjectSerializer, CustomQuestionSerializer, CheckAnswersSerializer, ChapterSerializer
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
        student = Student.objects.filter(user=request.user).first()
        if not student or not student.class_name:
            return Response({"message": "Foydalanuvchining sinfi topilmadi"}, status=400)

        # class_name: "4-sinf Matematika" -> Extract class number and subject name
        match = re.match(r"(\d+)-sinf\s+(.+)", student.class_name.strip())
        if not match:
            return Response({"message": "Sinf formati noto‘g‘ri, masalan: '4-sinf Matematika'"}, status=400)

        current_class_num = int(match.group(1))
        subject_name = match.group(2).strip()

        prev_class_num = current_class_num - 1
        if prev_class_num < 1:
            return Response({"message": "Quyi sinf mavjud emas"}, status=400)

        # Subject nomini normalize qilish
        expected_name = f"{prev_class_num}-sinf {subject_name}".strip().lower().replace(" ", "")

        # Subjectni sinf va nomi bo‘yicha qidiramiz
        matched_subject = None
        for subject in Subject.objects.all():
            class_uz = f"{subject.classes.name}-sinf {subject.name_uz}".strip().lower().replace(" ", "")
            if class_uz == expected_name:
                matched_subject = subject
                break

        if not matched_subject:
            all_available = [
                f"{subj.classes.name}-sinf {subj.name_uz}" for subj in Subject.objects.all()
            ]
            return Response({
                "message": f"{prev_class_num}-sinf '{subject_name}' fani topilmadi",
                "available_subjects": all_available
            }, status=400)

        chapters = matched_subject.chapters.all()
        if not chapters.exists():
            return Response({"message": "Bo‘limlar topilmadi"}, status=400)

        level = request.data.get("level")
        try:
            level = int(level)
        except (TypeError, ValueError):
            return Response({"message": "Level noto‘g‘ri formatda, butun son bo‘lishi kerak"}, status=400)

        total_questions = 30
        per_chapter = total_questions // chapters.count()
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

        serializer = CustomQuestionSerializer(questions_list, many=True, context={'request': request})
        filtered_data = list(filter(None, serializer.data))
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
            student_class_name = student.class_name.strip()

            # 2. Subject querysetni olib, filter qilamiz
            matched_subjects = []

            for subject in Subject.objects.all():
                class_uz = f"{subject.classes.name}-sinf {subject.name_uz}"
                class_ru = f"{subject.classes.name}-класс {subject.name_ru}"
                
                if student_class_name in [class_uz, class_ru]:
                    matched_subjects.append(subject)

            serializer = SubjectSerializer(matched_subjects, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Student.DoesNotExist:
            return Response({"detail": "Student topilmadi"}, status=status.HTTP_404_NOT_FOUND)


class ChapterListBySubjectAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, subject_id):
        try:
            # 1. Subject obyektini olish
            subject = Subject.objects.get(id=subject_id)

            # 2. Shu subjectga tegishli barcha chapterlarni olish
            chapters = Chapter.objects.filter(subject=subject)

            # 3. Serialize qilish
            serializer = ChapterSerializer(chapters, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Subject.DoesNotExist:
            return Response({"detail": "Subject topilmadi"}, status=status.HTTP_404_NOT_FOUND)

