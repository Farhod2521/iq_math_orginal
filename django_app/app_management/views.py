from rest_framework.generics import ListAPIView
from .models import SystemSettings, FAQ, Product, Banner
from .serializers import SystemSettingsSerializer, FAQSerializer, ProductSerializer, BannerSerializer
from django_app.app_user.models import User, Teacher, Student
from django_app.app_payments.models import Subscription, Payment
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


class BannerListView(ListAPIView):
    queryset = Banner.objects.all()
    serializer_class = BannerSerializer

class ProductListView(ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer



class StatisticsAPIView(APIView):
    def get(self, request):
        total_teachers = Teacher.objects.count()
        total_students = Student.objects.count()

        today = timezone.now()
        five_days_later = today + timedelta(days=5)

        # 5 kun ichida muddati tugaydigan va hali to'lamagan obunalar
        due_soon_subscriptions = Subscription.objects.filter(
            is_paid=False,
            end_date__lte=five_days_later,
            end_date__gte=today
        ).count()

        # To'lov statistikasi
        total_payments = Payment.objects.count()
        pending_payments = Payment.objects.filter(status='pending').count()
        success_payments = Payment.objects.filter(status='success').count()
        failed_payments = Payment.objects.filter(status='failed').count()

        data = {
            "total_teachers": total_teachers,
            "total_students": total_students,
            "students_due_within_5_days": due_soon_subscriptions,
            "total_payments": total_payments,
            "pending_payments": pending_payments,
            "successful_payments": success_payments,
            "failed_payments": failed_payments
        }

        return Response(data)







