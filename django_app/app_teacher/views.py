from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Subject, Chapter, Topic, Question, Choice, CompositeSubQuestion
from .serializers import(
    SubjectSerializer, MyChapterAddSerializer, MyTopicAddSerializer,
    ChoiceSerializer, CompositeSubQuestionSerializer, QuestionSerializer
)
from django.shortcuts import get_object_or_404





class TeacherSubjectsAPIView(APIView):
    permission_classes = [IsAuthenticated]  # Faqat tizimga kirgan foydalanuvchilar

    def get(self, request):
        teacher = request.user.teacher_profile  # Tizimga kirgan o‘qituvchini olish
        subjects = Subject.objects.filter(teachers=teacher)  # O‘qituvchiga bog‘langan fanlar

        serializer = SubjectSerializer(subjects, many=True)  
        return Response(serializer.data)
    
class MyChapterAddCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        teacher = request.user.teacher_profile
        subject_id = request.data.get("subject")

        if not subject_id:
            return Response({"error": "Fan ID majburiy!"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            subject = Subject.objects.get(id=subject_id, teachers=teacher)
        except Subject.DoesNotExist:
            return Response({"error": "Siz bu fanga bo'lim qo'sha olmaysiz!"}, status=status.HTTP_403_FORBIDDEN)

        serializer = MyChapterAddSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(subject=subject)  # yoki kerakli boshqa fieldlar
            return Response({"message": "Chapter yaratildi!", "data": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyTopicAddCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        teacher = request.user.teacher_profile
        chapter_id = request.data.get("chapter")

        if not chapter_id:
            return Response({"error": "Chapter ID majburiy!"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            chapter = Chapter.objects.get(id=chapter_id, subject__teachers=teacher)
        except Chapter.DoesNotExist:
            return Response({"error": "Siz bu bo‘limga mavzu qo‘sha olmaysiz!"}, status=status.HTTP_403_FORBIDDEN)

        serializer = MyTopicAddSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(chapter=chapter)  # kerakli bo‘lsa `chapter`ni o‘zing kirit
            return Response({"message": "Topic yaratildi!", "data": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
from django.db import transaction
   
class QuestionAddCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        serializer = QuestionSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    # Savolni yaratish
                    question = serializer.save(created_by=user)

                    # Choice savollarini saqlash
                    if question.question_type in ['choice', 'image_choice']:
                        choices_data = request.data.get('choices', [])
                        if not choices_data:
                            raise ValueError("Choice savollar uchun variantlar kiritilmagan")
                        
                        # Avvalgi choicelarni o'chirish
                        question.choices.all().delete()
                        
                        # Yangi choicelarni yaratish
                        choices = []
                        for choice_data in choices_data:
                            choice = Choice(
                                question=question,
                                letter=choice_data.get('letter'),
                                text=choice_data.get('text'),
                                image=choice_data.get('image'),
                                is_correct=choice_data.get('is_correct', False)
                            )
                            choices.append(choice)
                        
                        # Bulk create qilish
                        Choice.objects.bulk_create(choices)

                    # Composite savollarini saqlash
                    elif question.question_type == 'composite':
                        sub_questions_data = request.data.get('sub_questions', [])
                        if not sub_questions_data:
                            raise ValueError("Composite savol uchun kichik savollar kiritilmagan")
                        
                        # Avvalgi sub_questionlarni o'chirish
                        question.sub_questions.all().delete()
                        
                        # Yangi sub_questionlarni yaratish
                        sub_questions = []
                        for sub_data in sub_questions_data:
                            sub_question = CompositeSubQuestion(
                                question=question,
                                text1=sub_data.get('text1'),
                                correct_answer=sub_data.get('correct_answer'),
                                text2=sub_data.get('text2')
                            )
                            sub_questions.append(sub_question)
                        
                        # Bulk create qilish
                        CompositeSubQuestion.objects.bulk_create(sub_questions)

                    # Savolni yangilangan holatda qaytarish
                    question.refresh_from_db()
                    return Response(QuestionSerializer(question).data, status=status.HTTP_201_CREATED)

            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({"error": f"Server xatosi: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class MyChapterListView(APIView):
    """Tizimga kirgan o‘qituvchining barcha bo‘limlarini olish"""
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        teacher = request.user.teacher_profile  
        subjects = Subject.objects.filter(teachers=teacher)  
        chapters = Chapter.objects.filter(subject__in=[id])  

        serializer = MyChapterAddSerializer(chapters, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, id):
        chapter = get_object_or_404(Chapter, id=id)
        serializer = MyChapterAddSerializer(chapter, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        chapter = get_object_or_404(Chapter, id=id)
        chapter.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    
class MyTopicListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
    
        topics = Topic.objects.filter(chapter__in=[id])

        serializer = MyTopicAddSerializer(topics, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    def put(self, request, id):
        topic = get_object_or_404(Topic, id=id)
        serializer = MyTopicAddSerializer(topic, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        topic = get_object_or_404(Topic, id=id)
        topic.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# class MyQuestionListView(APIView):
#     """Tizimga kirgan o‘qituvchining barcha savollarini olish"""
#     permission_classes = [IsAuthenticated]

#     def get(self, request, id):
#         questions = Question.objects.filter(topic__in=[id])

#         serializer = MyQuestionAddSerializer(questions, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)  
    
#     def put(self, request, id):
#         question = get_object_or_404(Question, id=id)
#         serializer = MyQuestionAddSerializer(question, data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#     def delete(self, request, id):
#         question = get_object_or_404(Question, id=id)
#         question.delete()
#         return Response(status=status.HTTP_204_NO_CONTENT)