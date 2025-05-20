from rest_framework.generics import ListAPIView
from .models import SystemSettings, FAQ, Product
from .serializers import SystemSettingsSerializer, FAQSerializer, ProductSerializer
from django_app.app_user.models import User, Teacher, Student
from rest_framework.views import APIView
from rest_framework.response import Response
class SystemSettingsListView(ListAPIView):
    queryset = SystemSettings.objects.all()
    serializer_class = SystemSettingsSerializer


class FAQListView(ListAPIView):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer

class ProductListView(ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class StatisticsAPIView(APIView):

    def get(self, request):
        total_users = User.objects.count()
        total_teachers = Teacher.objects.count()
        total_students = Student.objects.count()

        data = {
            "total_users": total_users,
            "total_teachers": total_teachers,
            "total_students": total_students,
        }

        return Response(data)