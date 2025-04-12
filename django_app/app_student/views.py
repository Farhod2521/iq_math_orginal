from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_app.app_teacher.models import Subject, Topic, Question, Chapter, Subject_Category
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
        student = getattr(request.user, 'student_profile', None)
        if not student or not student.class_name:
            return Response({"message": "Sinf topilmadi"}, status=400)

        try:
            level = int(request.data.get("level", 0))
        except (ValueError, TypeError):
            return Response({"message": "Level noto‘g‘ri formatda yoki mavjud emas"}, status=400)

        all_classes = list(Class.objects.all())
        all_classes.sort(key=lambda c: int(c.name))  # bu yerda string emas, int bilan sort qilinyapti

        student_class = student.class_name

        try:
            current_index = all_classes.index(student_class)
        except ValueError:
            return Response({"message": "Foydalanuvchining sinfi ro'yxatda yo‘q"}, status=400)

        # Agar eng pastgi sinf bo‘lsa (1-sinf), unda o‘zidan past sinf yo‘q
        if current_index == 0:
            return Response({"message": "Quyi sinf topilmadi"}, status=400)

        target_class = all_classes[current_index - 1]
        try:
            math_category = Subject_Category.objects.get(name__iexact="matematika")
        except Subject_Category.DoesNotExist:
            return Response({"message": "Matematika kategoriyasi topilmadi"}, status=400)

        subjects = Subject.objects.filter(
            classes=target_class,
            category=math_category
        ).prefetch_related("chapters")

        questions = []

        for subject in subjects:
            chapters = Chapter.objects.filter(subject=subject)
            chapter_count = chapters.count()
            if chapter_count == 0:
                continue

            per_chapter = max(1, 30 // chapter_count)

            for chapter in chapters:
                chapter_questions = list(
                    Question.objects.filter(topic__chapter=chapter, level=level)
                    .prefetch_related('choices', 'sub_questions')
                )
                if chapter_questions:
                    questions.extend(random.sample(chapter_questions, min(per_chapter, len(chapter_questions))))

        questions = random.sample(questions, min(30, len(questions)))

        data = []
        for q in questions:
            q_data = {
                "id": q.id,
                "question_text": q.question_text,
                "question_type": q.question_type,
                "topic": q.topic.name,
            }

            if q.question_type == 'choice':
                q_data["choices"] = [
                    {
                        "letter": choice.letter,
                        "text": choice.text,
                        "is_correct": choice.is_correct  # bu qatorni faqat adminlar uchun ko‘rsatish mumkin
                    } for choice in q.choices.all()
                ]
            elif q.question_type == 'image_choice':
                q_data["choices"] = [
                    {
                        "letter": choice.letter,
                        "image_url": choice.image.url if choice.image else None,
                        "is_correct": choice.is_correct
                    } for choice in q.choices.all()
                ]
            elif q.question_type == 'text':
                # Faqat savol, javobni yubormaymiz
                q_data["answer_type"] = "text"
            elif q.question_type == 'composite':
                q_data["sub_questions"] = [
                    {
                        "text1": sub.text1,
                        "text2": sub.text2,
                        "correct_answer": sub.correct_answer
                    } for sub in q.sub_questions.all()
                ]

            data.append(q_data)

        return Response({"questions": data})



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
