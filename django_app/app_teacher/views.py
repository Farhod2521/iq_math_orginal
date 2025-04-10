from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Subject, Chapter, Topic, Question
from .serializers import(
    SubjectSerializer, MyChapterAddSerializer, MyTopicAddSerializer
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
    
# class QuestionAddCreateView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         teacher = request.user.teacher_profile
#         topic_id = request.data.get("topic")

#         if not topic_id:
#             return Response({"error": "Topic ID majburiy!"}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             topic = Topic.objects.get(id=topic_id, chapter__subject__teachers=teacher)
#         except Topic.DoesNotExist:
#             return Response({"error": "Siz bu mavzuga savol qo‘sha olmaysiz!"}, status=status.HTTP_403_FORBIDDEN)

#         data = request.data.copy()
#         files = request.FILES

#         # Agar `images` fayllari bir nechta bo‘lsa, ularni to‘g‘ri formatga o‘tkazish kerak
#         images = []
#         index = 0
#         while f'images[{index}].image' in files:
#             images.append({
#                 "image": files.get(f'images[{index}].image'),
#                 "choice_letter": data.get(f'images[{index}].choice_letter')
#             })
#             index += 1

#         # Yangi strukturani serializerga beramiz
#         combined_data = data
#         combined_data.setlist('images', images)

#         serializer = MyQuestionAddSerializer(data={"question_text": data.get("question_text"),
#                                                    "question_type": data.get("question_type"),
#                                                    "correct_answer": data.get("correct_answer"),
#                                                    "level": data.get("level"),
#                                                    "choices": data.get("choices"),
#                                                    "images": images})
#         if serializer.is_valid():
#             question = serializer.save(topic=topic)
#             return Response({"message": "Savol yaratildi!", "data": MyQuestionAddSerializer(question).data},
#                             status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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