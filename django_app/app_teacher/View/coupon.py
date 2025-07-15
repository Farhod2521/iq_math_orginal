from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone
from datetime import timedelta

from django_app.app_user.models import Teacher
from django_app.app_management.models import  Coupon, ReferralAndCouponSettings

class CreateTeacherCouponAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # Faqat Teacher profili borligini tekshiramiz
        try:
            teacher = user.teacher_profile
        except Teacher.DoesNotExist:
            return Response({"error": "Teacher profili mavjud emas."}, status=status.HTTP_400_BAD_REQUEST)

        # Sozlamalarni olish
        settings = ReferralAndCouponSettings.objects.last()
        if not settings:
            return Response({"error": "Kupon sozlamalari topilmadi."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Amal qilish muddatini belgilash
        valid_until = timezone.now() + timedelta(days=settings.coupon_valid_days)

        # Kupon yaratish
        coupon = Coupon.objects.create(
            discount_percent=settings.coupon_discount_percent,
            valid_from=timezone.now(),
            valid_until=valid_until,
            created_by_teacher=teacher,
            is_active=True
        )

        return Response({
            "message": "Kupon yaratildi",
            "coupon_code": coupon.code,
            "discount_percent": coupon.discount_percent,
            "valid_until": coupon.valid_until
        }, status=status.HTTP_201_CREATED)
