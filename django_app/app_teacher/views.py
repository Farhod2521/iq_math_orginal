from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Subject
from .serializers import SubjectSerializer





class TeacherSubjectsAPIView(APIView):
    permission_classes = [IsAuthenticated]  # Faqat tizimga kirgan foydalanuvchilar

    def get(self, request):
        teacher = request.user.teacher_profile  # Tizimga kirgan o‘qituvchini olish
        subjects = Subject.objects.filter(teachers=teacher)  # O‘qituvchiga bog‘langan fanlar

        serializer = SubjectSerializer(subjects, many=True)  
        return Response(serializer.data)