from rest_framework.generics import ListAPIView
from .models import SystemSettings, FAQ, Product
from .serializers import SystemSettingsSerializer, FAQSerializer, ProductSerializer
from django_app.app_user.models import User, Teacher, Student
from django_app.app_payments.models import Subscription
from rest_framework.views import APIView
from rest_framework.response import Response

from django.utils import timezone
from datetime import timedelta

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

        # Bugungi sana va 5 kundan keyingi sana
        today = timezone.now()
        five_days_later = today + timedelta(days=5)

        # 5 kun ichida to'lov qilishi kerak bo'lgan studentlar
        due_soon_subscriptions = Subscription.objects.filter(
            is_paid=False,
            next_payment_date__lte=five_days_later,
            next_payment_date__gte=today
        ).count()

        data = {
            "total_users": total_users,
            "total_teachers": total_teachers,
            "total_students": total_students,
            "students_due_within_5_days": due_soon_subscriptions
        }

        return Response(data)
