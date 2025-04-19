from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_app.app_teacher.models import Subject, Topic, Question, Chapter, Subject_Category, CompositeSubQuestion, Choice
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


###################################   TIZIMGA KIRGAN O"QUVCHI BILIM DARAJASINI TEKSHIRISH #####################

class GenerateTestAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        student = Student.objects.filter(user=request.user).first()
        if not student or not student.class_name:
            return Response({"message": "Foydalanuvchining sinfi topilmadi"}, status=400)

        # 4-sinf Matematika -> 4
        import re
        match = re.match(r"(\d+)", student.class_name)
        if not match:
            return Response({"message": "Sinf raqami noto‘g‘ri formatda"}, status=400)

        current_class_num = int(match.group(1))
        prev_class_num = current_class_num - 1

        try:
            prev_class = Class.objects.get(name=str(prev_class_num))
        except Class.DoesNotExist:
            return Response({"message": f"{prev_class_num}-sinf topilmadi"}, status=400)

        subjects = Subject.objects.filter(
            classes=prev_class,
            category__name__iexact="Matematika"
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

        serializer = CustomQuestionSerializer(questions_list, many=True, context={'request': request})
        filtered_data = list(filter(None, serializer.data))  # None bo‘lganlarini olib tashlash
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

