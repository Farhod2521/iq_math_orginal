from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Subject, Chapter, Topic, Question
from .serializers import(
    SubjectSerializer, MyChapterAddSerializer, MyTopicAddSerializer,
    MyQuestionAddSerializer, MyQuestionImageAddSerializer
)






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
        teacher = request.user.teacher_profile  # Tizimga kirgan o‘qituvchi
        subjects = Subject.objects.filter(teachers=teacher)  # O'qituvchiga tegishli fanlar

        subject_id = request.data.get("subject")  # Foydalanuvchi tanlagan fan ID si
        if not subject_id:
            return Response({"error": "Fan ID majburiy!"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            subject = subjects.get(id=subject_id)  # O'qituvchiga tegishli fan bormi?
        except Subject.DoesNotExist:
            return Response({"error": "Siz bu fanga bo'lim qo'sha olmaysiz!"}, status=status.HTTP_403_FORBIDDEN)

        serializer = MyChapterAddSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Chapter yaratildi!", "data": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyTopicAddCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        teacher = request.user.teacher_profile  # Tizimga kirgan o‘qituvchi
        subjects = Subject.objects.filter(teachers=teacher)  # O‘qituvchiga tegishli fanlar
        chapters = Chapter.objects.filter(subject__in=subjects)  # Ushbu fanlarga tegishli bo‘limlar

        chapter_id = request.data.get("chapter")  # Foydalanuvchi yuborgan chapter ID
        if not chapter_id:
            return Response({"error": "Chapter ID majburiy!"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            chapter = chapters.get(id=chapter_id)  # Faqat o‘qituvchiga tegishli bo‘limni olish
        except Chapter.DoesNotExist:
            return Response({"error": "Siz bu bo‘limga mavzu qo‘sha olmaysiz!"}, status=status.HTTP_403_FORBIDDEN)

        serializer = MyTopicAddSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Topic yaratildi!", "data": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class QuestionAddCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        teacher = request.user.teacher_profile  
        subjects = Subject.objects.filter(teachers=teacher)  
        chapters = Chapter.objects.filter(subject__in=subjects)  
        topics = Topic.objects.filter(chapter__in=chapters)  

        topic_id = request.data.get("topic")  # Foydalanuvchi yuborgan topic ID
        if not topic_id:
            return Response({"error": "Topic ID majburiy!"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            topic = topics.get(id=topic_id)  # O'qituvchiga tegishli topic bormi?
        except Topic.DoesNotExist:
            return Response({"error": "Siz bu mavzuga savol qo‘sha olmaysiz!"}, status=status.HTTP_403_FORBIDDEN)

        serializer = MyQuestionAddSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Savol yaratildi!", "data": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class MyChapterListView(APIView):
    """Tizimga kirgan o‘qituvchining barcha bo‘limlarini olish"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        teacher = request.user.teacher_profile  
        subjects = Subject.objects.filter(teachers=teacher)  
        chapters = Chapter.objects.filter(subject__in=subjects)  

        serializer = MyChapterAddSerializer(chapters, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MyTopicListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
    
        topics = Topic.objects.filter(chapter__in=id)

        serializer = MyTopicAddSerializer(topics, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MyQuestionListView(APIView):
    """Tizimga kirgan o‘qituvchining barcha savollarini olish"""
    # permission_classes = [IsAuthenticated]

    def get(self, request, id):
        questions = Question.objects.filter(topic__in=id)

        serializer = MyQuestionAddSerializer(questions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)    