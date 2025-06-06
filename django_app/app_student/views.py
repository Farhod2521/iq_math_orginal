from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_app.app_teacher.models import  Topic, Question, Chapter, CompositeSubQuestion, Choice
from django_app.app_user.models import  Subject, Subject_Category
from django_app.app_user.models import Student, Class
from .serializers import (
    SubjectSerializer, CustomQuestionSerializer, CheckAnswersSerializer, ChapterSerializer, 
    TopicSerializer, TopicSerializer1
    )
import random
from django.db.models import Q
from collections import defaultdict
from bs4 import BeautifulSoup  # HTML teglarini tozalash uchun
from django.utils.html import strip_tags
from random import sample
from .models import Diagnost_Student, TopicProgress, StudentScoreLog, StudentScore
from rest_framework import status
from django.utils import timezone
import re
from django.shortcuts import get_object_or_404
###################################   TIZIMGA KIRGAN O"QUVCHI BILIM DARAJASINI TEKSHIRISH #####################
from django.utils.timezone import now
from django_app.app_payments.models import Subscription
from random import sample

class GenerateTestAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        student = Student.objects.get(user=request.user)
        if not student or not student.class_name:
            return Response({"message": "Foydalanuvchining sinfi topilmadi"}, status=400)

        current_class_name = student.class_name.classes.name

        try:
            current_class = Class.objects.get(name=current_class_name)
        except Class.DoesNotExist:
            return Response({"message": "Joriy sinf topilmadi"}, status=400)

        try:
            level = int(request.data.get("level"))
        except (TypeError, ValueError):
            return Response({"message": "Level noto‘g‘ri formatda"}, status=400)

        def get_questions_by_class(cls, count):
            subjects = Subject.objects.filter(classes=cls, category__name__iexact="Matematika")
            if not subjects.exists():
                return []
            subject = subjects.first()
            chapters = subject.chapters.all()
            questions = Question.objects.filter(topic__chapter__in=chapters, level=level).distinct()
            return sample(list(questions), min(count, questions.count()))

        if current_class_name == "5":
            # faqat 5-sinfdan 30 ta
            questions_list = get_questions_by_class(current_class, 30)
        else:
            # 15 ta joriy sinf, 15 ta quyi sinf
            try:
                prev_class = Class.objects.get(name=str(int(current_class_name) - 1))
            except (ValueError, Class.DoesNotExist):
                return Response({"message": "Quyi sinf topilmadi"}, status=400)

            current_qs = get_questions_by_class(current_class, 15)
            prev_qs = get_questions_by_class(prev_class, 15)
            questions_list = current_qs + prev_qs

        serializer = CustomQuestionSerializer(questions_list, many=True, context={'request': request})
        filtered_data = list(filter(None, serializer.data))

        return Response(filtered_data)


class GenerateCheckAnswersAPIView(APIView):
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
        wrong_topics = {}
        wrong_topic_instances = set()  # <- faqat xato mavzular uchun

        index = 1

        def add_wrong_topic(question):
            if question.topic:
                wrong_topic_instances.add(question.topic)
                if question.topic.name_uz not in wrong_topics:
                    wrong_topics[question.topic.name_uz] = {
                        'index': len(wrong_topics) + 1,
                        'topic_name_ru': question.topic.name_ru,
                        'topic_name_uz': question.topic.name_uz
                    }

        # TEXT QUESTIONS
        for answer in serializer.validated_data.get('text_answers', []):
            question = Question.objects.filter(id=answer['question_id'], question_type='text').first()
            if not question:
                continue

            student_answer = answer.get('answer_uz') or answer.get('answer_ru')
            correct_answer = question.correct_text_answer_uz if 'answer_uz' in answer else question.correct_text_answer_ru

            if student_answer is None or correct_answer is None:
                continue

            student_answer_plain = strip_tags(student_answer).strip()
            correct_answer_plain = strip_tags(correct_answer).strip()
            is_correct = (student_answer_plain == correct_answer_plain)

            total_answers += 1
            if is_correct:
                correct_answers += 1
            else:
                add_wrong_topic(question)

            question_details.append({
                "index": index,
                "question_id": question.id,
                "question_uz": question.question_text_uz,
                "question_ru": question.question_text_ru,
                "answer": is_correct
            })
            index += 1

        # CHOICE QUESTIONS
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
                add_wrong_topic(question)

            question_details.append({
                "index": index,
                "question_id": question.id,
                "question_uz": question.question_text_uz,
                "question_ru": question.question_text_ru,
                "answer": is_correct
            })
            index += 1

        # COMPOSITE QUESTIONS
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
                add_wrong_topic(question)

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
            "Topic": list(wrong_topics.values()),
            "result": [{
                "total_answers": total_answers,
                "correct_answers": correct_answers,
                "score": score
            }]
        }

        first_question_id = question_details[0]['question_id'] if question_details else None
        level = Question.objects.filter(id=first_question_id).first().level if first_question_id else None

        diagnost = Diagnost_Student.objects.create(
            student=student_instance,
            level=level,
            result=result_json
        )

        # faqat xato qilingan savollarning topiclarini biriktiramiz
        diagnost.topic.set(wrong_topic_instances)

        return Response(result_json)





class StudentSubjectListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Agar o'qituvchi bo'lsa — barcha subjectlar ochiq bo'lib qaytariladi
        if hasattr(user, 'teacher_profile'):
            all_subjects = Subject.objects.all()
            result = []

            for subject in all_subjects:
                serialized = SubjectSerializer(subject).data
                serialized["is_open"] = True
                result.append(serialized)

            return Response(result, status=status.HTTP_200_OK)

        # Aks holda — talaba uchun ishlashni davom ettiramiz
        try:
            student = Student.objects.get(user=user)
            now_time = now()

            is_subscription_valid = False
            is_free_trial_active = False

            try:
                subscription = student.subscription
                if subscription.is_paid and subscription.start_date <= now_time <= subscription.end_date:
                    is_subscription_valid = True
                elif not subscription.is_paid and subscription.start_date <= now_time <= subscription.end_date:
                    is_free_trial_active = True
            except Subscription.DoesNotExist:
                pass

            all_subjects = Subject.objects.all()
            result = []

            for subject in all_subjects:
                serialized = SubjectSerializer(subject).data
                if is_subscription_valid or is_free_trial_active:
                    serialized["is_open"] = True
                else:
                    serialized["is_open"] = False
                result.append(serialized)

            return Response(result, status=status.HTTP_200_OK)

        except Student.DoesNotExist:
            return Response({"detail": "Student topilmadi"}, status=status.HTTP_404_NOT_FOUND)


class ChapterListBySubjectAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, subject_id):
        try:
            subject = Subject.objects.get(id=subject_id)
            chapters = Chapter.objects.filter(subject=subject)
            serializer = ChapterSerializer(chapters, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Subject.DoesNotExist:
            return Response({"detail": "Subject topilmadi"}, status=status.HTTP_404_NOT_FOUND)
        
class TopicListByChapterAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, chapter_id):
        user = request.user

        # Agar teacher_profile mavjud bo‘lsa, obuna tekshiruvisiz ko‘rsatamiz
        if hasattr(user, 'teacher_profile'):
            try:
                chapter = Chapter.objects.get(id=chapter_id)
                topics = Topic.objects.filter(chapter=chapter)
                serializer = TopicSerializer(topics, many=True, context={'request': request})
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Chapter.DoesNotExist:
                return Response({"detail": "Chapter topilmadi"}, status=status.HTTP_404_NOT_FOUND)

        # Student bo‘lsa, obuna va progress tekshiriladi
        student = getattr(user, 'student_profile', None)

        if not student:
            return Response({"detail": "Foydalanuvchi uchun student profili topilmadi"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            subscription = student.subscription
        except Subscription.DoesNotExist:
            return Response({"detail": "Obuna mavjud emas. To‘lovni amalga oshiring"}, status=status.HTTP_403_FORBIDDEN)

        if subscription.end_date < timezone.now():
            return Response({"detail": "Obuna muddati tugagan. Iltimos, to‘lovni amalga oshiring."}, status=status.HTTP_403_FORBIDDEN)

        try:
            chapter = Chapter.objects.get(id=chapter_id)
            topics = Topic.objects.filter(chapter=chapter)
            serializer = TopicSerializer(topics, many=True, context={'request': request})
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
        

from django.utils.html import strip_tags
from .math_answer_check import advanced_math_check  

class CheckAnswersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CheckAnswersSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"message": "Noto‘g‘ri formatdagi ma'lumotlar."}, status=400)

        is_teacher = hasattr(request.user, 'teacher_profile')
        student_instance = None
        student_score = None
        awarded_questions = set()

        if not is_teacher:
            try:
                student_instance = Student.objects.get(user=request.user)
                student_score, _ = StudentScore.objects.get_or_create(student=student_instance)
                awarded_questions = set(
                    StudentScoreLog.objects.filter(student_score=student_score).values_list('question_id', flat=True)
                )
            except Student.DoesNotExist:
                return Response({"message": "Student topilmadi"}, status=404)

        correct_answers = 0
        total_answers = 0
        question_details = []
        index = 1
        last_question_topic = None

        # TEXT ANSWERS
        for answer in serializer.validated_data.get('text_answers', []):
            question = Question.objects.filter(id=answer['question_id'], question_type='text').first()
            if not question:
                continue

            student_answer = answer.get('answer_uz') or answer.get('answer_ru')
            correct_answer = question.correct_text_answer_uz if 'answer_uz' in answer else question.correct_text_answer_ru

            if student_answer is None or correct_answer is None:
                continue

            is_correct = advanced_math_check(strip_tags(student_answer).strip(), strip_tags(correct_answer).strip())
            total_answers += 1
            if is_correct:
                correct_answers += 1
                if not is_teacher and question.id not in awarded_questions:
                    student_score.score += 1
                    awarded_questions.add(question.id)
                    StudentScoreLog.objects.create(student_score=student_score, question=question)

            last_question_topic = question.topic
            question_details.append({
                "index": index,
                "question_id": question.id,
                "question_uz": question.question_text_uz,
                "question_ru": question.question_text_ru,
                "answer": is_correct
            })
            index += 1

        # CHOICE ANSWERS
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
                if not is_teacher and question.id not in awarded_questions:
                    student_score.score += 1
                    awarded_questions.add(question.id)
                    StudentScoreLog.objects.create(student_score=student_score, question=question)

            last_question_topic = question.topic
            question_details.append({
                "index": index,
                "question_id": question.id,
                "question_uz": question.question_text_uz,
                "question_ru": question.question_text_ru,
                "answer": is_correct
            })
            index += 1

        # COMPOSITE ANSWERS
        for answer in serializer.validated_data.get('composite_answers', []):
            question = Question.objects.filter(id=answer['question_id'], question_type='composite').first()
            if not question:
                continue

            correct_subs = question.sub_questions.all()
            is_correct = all(sub_answer == sub_q.correct_answer for sub_answer, sub_q in zip(answer['answers'], correct_subs))

            total_answers += 1
            if is_correct:
                correct_answers += 1
                if not is_teacher and question.id not in awarded_questions:
                    student_score.score += 1
                    awarded_questions.add(question.id)
                    StudentScoreLog.objects.create(student_score=student_score, question=question)

            last_question_topic = question.topic
            question_details.append({
                "index": index,
                "question_id": question.id,
                "question_uz": question.question_text_uz,
                "question_ru": question.question_text_ru,
                "answer": is_correct
            })
            index += 1

        score = round((correct_answers / total_answers) * 100, 2) if total_answers else 0.0

        # Agar bu teacher bo'lmasa, ma'lumotlarni saqlaymiz
        if not is_teacher:
            student_score.save()

            if last_question_topic and score >= 80:
                topic_progress, _ = TopicProgress.objects.get_or_create(
                    user=student_instance, topic=last_question_topic
                )
                topic_progress.is_unlocked = True
                topic_progress.score = score
                topic_progress.completed_at = timezone.now()
                topic_progress.save()

                all_topics = Topic.objects.filter(chapter=last_question_topic.chapter, is_locked=False).order_by('id')
                topic_ids = list(all_topics.values_list('id', flat=True))

                if last_question_topic.id in topic_ids:
                    current_index = topic_ids.index(last_question_topic.id)
                    if current_index + 1 < len(topic_ids):
                        next_topic = Topic.objects.get(id=topic_ids[current_index + 1])
                        next_progress, created = TopicProgress.objects.get_or_create(
                            user=student_instance, topic=next_topic
                        )
                        if created:
                            next_progress.is_unlocked = True
                            next_progress.save()

        return Response({
            "question": question_details,
            "result": [{
                "total_answers": total_answers,
                "correct_answers": correct_answers,
                "score": score
            }]
        })




#############################   STUDENT BALL ###############################

class StudentScoreAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Agar teacher bo‘lsa, oddiy javob qaytariladi
        if hasattr(user, 'teacher_profile'):
            return Response({
                "detail": "Bu sahifa faqat talaba profili uchun mo‘ljallangan.",
                "score": 9999
            }, status=status.HTTP_200_OK)

        # Talaba uchun davom etadi
        try:
            student = Student.objects.get(user=user)
        except Student.DoesNotExist:
            return Response({"detail": "Talaba topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        try:
            score_obj = StudentScore.objects.get(student=student)
            return Response({
                "student": student.full_name,
                "score": score_obj.score,
                "created_at": score_obj.created_at
            })
        except StudentScore.DoesNotExist:
            return Response({
                "student": student.full_name,
                "score": 0,
                "message": "Hozircha sizga hech qanday ball biriktirilmagan."
            })


class DiagnostLevelOverviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        student = Student.objects.get(user=user)
        levels = [1, 2, 3]
        data = []

        for lvl in levels:
            diagnost = Diagnost_Student.objects.filter(student=student, level=lvl).order_by('-id').first()
            if diagnost:
                score = diagnost.result['result'][0]['score']
                data.append({
                    "level": lvl,
                    "score": score
                })
            else:
                data.append({
                    "level": lvl,
                    "score": None,
                    "message": "Bu level uchun hali test topshirilmagan"
                })

        return Response(data)
    
class DiagnostLevelDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        student = Student.objects.get(user=user)
        level = request.query_params.get('level')

        if not level:
            return Response({"error": "Level parametrini yuboring"}, status=400)

        try:
            level = int(level)
        except ValueError:
            return Response({"error": "Level butun son bo'lishi kerak"}, status=400)

        diagnost = Diagnost_Student.objects.filter(student=student, level=level).order_by('-id').first()
        if not diagnost:
            return Response({"message": "Bu level uchun hali test topshirilmagan"}, status=404)

        topics = diagnost.topic.all()
        topic_list = [
            {"id": topic.id, "name_uz": topic.name_uz, "name_ru": topic.name_ru}
            for topic in topics
        ]

        return Response({
            "level": level,
            "topics": topic_list
        })
    

class Diagnostika_TopicDetailAPIView(APIView):
    def get(self, request, id):
        topic = get_object_or_404(Topic, id=id)
        serializer = TopicSerializer1(topic)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
import unicodedata

def slugify_uz(text):
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^\w\s-]', '', text.lower()).strip().replace(' ', '-')

def slugify_ru(text):
    return re.sub(r'\s+', '-', text.strip().lower())

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

class PathFromIdsAPIView(APIView):
    def post(self, request):
        subject_id = request.data.get("subject")
        chapter_id = request.data.get("chapter")
        topic_id = request.data.get("topic")  # optional

        if not subject_id:
            return Response({"error": "Subject ID majburiy"}, status=400)

        subject = get_object_or_404(Subject, id=subject_id)

        # Faqat subject bo'lsa, faqat subjectni qaytaramiz
        if not chapter_id:
            subject_data = {
                "id": str(subject.id),
                "title_uz": f"{subject.classes.name}-sinf {subject.name}",
                "title_ru": f"{subject.classes.name}-класс {subject.name}"
            }
            return Response([subject_data], status=status.HTTP_200_OK)

        # chapter bo‘lsa, uni ham qaytaramiz
        chapter = get_object_or_404(Chapter, id=chapter_id, subject=subject)
        response_data = [
            {
                "id": str(subject.id),
                "title_uz": f"{subject.classes.name}-sinf {subject.name}",
                "title_ru": f"{subject.classes.name}-класс {subject.name}"
            },
            {
                "id": str(chapter.id),
                "title_uz": chapter.name_uz,
                "title_ru": chapter.name_ru
            }
        ]

        # topic bo‘lsa, uni ham qo‘shamiz
        if topic_id:
            topic = get_object_or_404(Topic, id=topic_id, chapter=chapter)
            response_data.append({
                "id": str(topic.id),
                "title_uz": topic.name_uz,
                "title_ru": topic.name_ru
            })

        return Response(response_data, status=status.HTTP_200_OK)
