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
from .math_answer_check import compare_answers
class GenerateTestAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({"message": "Foydalanuvchi topilmadi"}, status=404)

        if not student.class_name:
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

        subject_id = request.data.get("subject_id")
        if subject_id:
            try:
                subject = Subject.objects.get(id=subject_id)
            except Subject.DoesNotExist:
                return Response({"message": "Berilgan subject_id bo‘yicha fan topilmadi"}, status=404)
        else:
            subjects = Subject.objects.filter(classes=current_class).order_by("id")
            if not subjects.exists():
                return Response({"message": "Ushbu sinf uchun hech qanday fan topilmadi"}, status=404)
            subject = subjects.first()

        chapters = subject.chapters.all()
        questions = Question.objects.filter(topic__chapter__in=chapters, level=level).distinct()
        question_list = sample(list(questions), min(30, questions.count()))

        serializer = CustomQuestionSerializer(question_list, many=True, context={'request': request})
        filtered_data = list(filter(None, serializer.data))

        return Response({
            "questions": filtered_data,
            "level": level,
            "subject_id": subject.id  # kerak bo‘lsa frontga subject qaytariladi
        })



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

        correct_answers, total_answers, index = 0, 0, 1
        question_details, wrong_topics = [], {}
        wrong_topic_instances = set()

        def add_wrong_topic(question):
            if question.topic:
                wrong_topic_instances.add(question.topic)
                if question.topic.name_uz not in wrong_topics:
                    wrong_topics[question.topic.name_uz] = {
                        'index': len(wrong_topics) + 1,
                        'topic_name_ru': question.topic.name_ru,
                        'topic_name_uz': question.topic.name_uz
                    }

        # TEXT
        for answer in serializer.validated_data.get('text_answers', []):
            question = Question.objects.filter(id=answer['question_id'], question_type='text').first()
            if not question:
                continue

            student_answer = answer.get('answer_uz') or answer.get('answer_ru')
            correct_answer = question.correct_text_answer_uz if 'answer_uz' in answer else question.correct_text_answer_ru
            if not student_answer or not correct_answer:
                continue

            is_correct = strip_tags(student_answer).strip() == strip_tags(correct_answer).strip()
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

        # CHOICE
        for answer in serializer.validated_data.get('choice_answers', []):
            question = Question.objects.filter(id=answer['question_id'], question_type='choice').first()
            if not question:
                continue

            correct_choices = set(Choice.objects.filter(question=question, is_correct=True).values_list('id', flat=True))
            selected_choices = set(answer['choices'])

            is_correct = correct_choices == selected_choices
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

        # COMPOSITE - BU QISMI O'ZGARDI!
        for answer in serializer.validated_data.get('composite_answers', []):
            question = Question.objects.filter(id=answer['question_id'], question_type='composite').first()
            if not question:
                continue

            correct_subs = question.sub_questions.all()
            student_answers = answer['answers']
            
            # Har bir sub question uchun javoblarni solishtiramiz
            all_correct = True
            for i, (student_ans, sub_question) in enumerate(zip(student_answers, correct_subs)):
                if not compare_answers(str(student_ans), str(sub_question.correct_answer)):
                    all_correct = False
                    break

            is_correct = all_correct
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

        # Fan, level va topiclardan subject aniqlaymiz
        subject = None
        level = None
        first_question = Question.objects.filter(id=question_details[0]['question_id']).select_related(
            'topic__chapter__subject').first() if question_details else None

        if first_question and first_question.topic and first_question.topic.chapter:
            subject = first_question.topic.chapter.subject
            level = first_question.level

        diagnost = Diagnost_Student.objects.create(
            student=student_instance,
            level=level,
            subject=subject,
            result=result_json
        )

        # Xato qilingan topic va chapterlarni yozamiz
        wrong_chapter_instances = set(topic.chapter for topic in wrong_topic_instances)
        diagnost.topic.set(wrong_topic_instances)
        diagnost.chapters.set(wrong_chapter_instances)

        return Response(result_json)





class StudentSubjectListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # 👉 Agar teacher yoki admin bo‘lsa — barcha fanlar to‘liq ochiq
        if user.role in ['teacher', 'admin']:
            all_subjects = Subject.objects.all().order_by('order')
            result = []

            for subject in all_subjects:
                serialized = SubjectSerializer(subject, context={
                    "is_open": True,
                    "is_diagnost_open": True
                }).data
                result.append(serialized)

            return Response(result, status=status.HTTP_200_OK)

        # 👉 Student bo‘lsa
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

            all_subjects = Subject.objects.filter(active=True).order_by('order')
            result = []

            for subject in all_subjects:
                has_diagnost = Diagnost_Student.objects.filter(student=student, subject=subject).exists()
                is_open = is_subscription_valid or is_free_trial_active

                serialized = SubjectSerializer(subject, context={
                    "is_open": is_open,
                    "is_diagnost_open": has_diagnost
                }).data

                result.append(serialized)

            return Response(result, status=status.HTTP_200_OK)

        except Student.DoesNotExist:
            return Response({"detail": "Student topilmadi"}, status=status.HTTP_404_NOT_FOUND)

class ChapterListBySubjectAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, subject_id):
        try:
            subject = Subject.objects.get(id=subject_id)
            chapters = Chapter.objects.filter(subject=subject).order_by('order')
            serializer = ChapterSerializer(chapters, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Subject.DoesNotExist:
            return Response({"detail": "Subject topilmadi"}, status=status.HTTP_404_NOT_FOUND)
        
class TopicListByChapterAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, chapter_id):
        user = request.user

        # 👨‍🏫👨‍💼 Agar teacher yoki admin bo‘lsa, to‘g‘ridan-to‘g‘ri barcha mavzular ko‘rsatiladi
        if user.role in ['teacher', 'admin']:
            try:
                chapter = Chapter.objects.get(id=chapter_id)
                topics = Topic.objects.filter(chapter=chapter).order_by('order')
                serializer = TopicSerializer(topics, many=True, context={'request': request})
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Chapter.DoesNotExist:
                return Response({"detail": "Chapter topilmadi"}, status=status.HTTP_404_NOT_FOUND)

        # 👩‍🎓 Student bo‘lsa, subscription tekshiriladi
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
            topics = Topic.objects.filter(chapter=chapter).order_by('order')
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
from .helper_coin import get_today_coin_count
class CheckAnswersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CheckAnswersSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"message": "Noto‘g‘ri formatdagi ma'lumotlar."}, status=400)

        # Admin yoki Teacher bo‘lsa student sifatida log yozilmaydi
        is_staff_user = request.user.role in ['teacher', 'admin']

        student_instance = None
        student_score = None
        awarded_questions = set()

        if not is_staff_user:
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
        today_coin_count = get_today_coin_count(student_score) if not is_staff_user else 0

        def process_question(question, is_correct):
            nonlocal correct_answers, student_score, awarded_questions, student_instance, today_coin_count

            if is_correct:
                correct_answers += 1

                if not is_staff_user and question.id not in awarded_questions:
                    awarded_questions.add(question.id)
                    student_score.score += 1

                    give_coin = False
                    if today_coin_count < 10:
                        student_score.coin += 1
                        today_coin_count += 1
                        give_coin = True

                    StudentScoreLog.objects.create(
                        student_score=student_score,
                        question=question,
                        awarded_coin=give_coin,
                        awarded_at=timezone.now()
                    )

        # TEXT SAVOLLAR
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
            process_question(question, is_correct)

            last_question_topic = question.topic
            question_details.append({
                "index": index,
                "question_id": question.id,
                "question_uz": question.question_text_uz,
                "question_ru": question.question_text_ru,
                "answer": is_correct,
                "answer_text": student_answer
            })
            index += 1

        # CHOICE SAVOLLAR
        for answer in serializer.validated_data.get('choice_answers', []):
            question = Question.objects.filter(id=answer['question_id'], question_type='choice').first()
            if not question:
                continue

            correct_choices = set(Choice.objects.filter(question=question, is_correct=True).values_list('id', flat=True))
            selected_choices = set(answer['choices'])
            is_correct = (correct_choices == selected_choices)

            total_answers += 1
            process_question(question, is_correct)

            last_question_topic = question.topic
            question_details.append({
                "index": index,
                "question_id": question.id,
                "question_uz": question.question_text_uz,
                "question_ru": question.question_text_ru,
                "answer": is_correct,
                "selected_choices": list(selected_choices)
            })
            index += 1

        # COMPOSITE SAVOLLAR
        for answer in serializer.validated_data.get('composite_answers', []):
            question = Question.objects.filter(id=answer['question_id'], question_type='composite').first()
            if not question:
                continue

            correct_subs = question.sub_questions.all()
            is_correct = all(sub_answer == sub_q.correct_answer for sub_answer, sub_q in zip(answer['answers'], correct_subs))

            total_answers += 1
            process_question(question, is_correct)

            last_question_topic = question.topic
            question_details.append({
                "index": index,
                "question_id": question.id,
                "question_uz": question.question_text_uz,
                "question_ru": question.question_text_ru,
                "answer": is_correct,
                "sub_answers": answer['answers']
            })
            index += 1

        score = round((correct_answers / total_answers) * 100, 2) if total_answers else 0.0

        # Faqat student uchun saqlaymiz
        if not is_staff_user:
            student_score.save()

            if last_question_topic:
                topic_progress, _ = TopicProgress.objects.get_or_create(
                    user=student_instance, topic=last_question_topic
                )
                if score > topic_progress.score:
                    topic_progress.score = score
                    topic_progress.completed_at = timezone.now()
                    topic_progress.save()

        response_data = {
            "question": question_details,
            "result": [{
                "total_answers": total_answers,
                "correct_answers": correct_answers,
                "score": score
            }]
        }

        # Qo‘shimcha info
        if last_question_topic:
            topic = last_question_topic
            chapter = topic.chapter
            subject = chapter.subject

            response_data["info"] = {
                "topic": {"id": topic.id},
                "chapter": {"id": chapter.id},
                "subject": {"id": subject.id}
            }

            first_question_with_level = Question.objects.filter(topic=topic).first()
            if first_question_with_level:
                response_data["level"] = first_question_with_level.level

        return Response(response_data)

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
                "coin": score_obj.coin,
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

