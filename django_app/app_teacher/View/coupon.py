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

        # Foydalanuvchi teacher ekanini tekshiramiz
        try:
            teacher = user.teacher_profile
        except Teacher.DoesNotExist:
            return Response({"error": "Teacher profili mavjud emas."}, status=status.HTTP_400_BAD_REQUEST)

        # Kupon kodi yuborilganmi?
        code = request.data.get("code")
        if not code:
            return Response({"error": "Kupon kodi kiritilmadi."}, status=status.HTTP_400_BAD_REQUEST)

        # Takrorlanmaganligini tekshiramiz
        if Coupon.objects.filter(code=code).exists():
            return Response({"error": "Bu kupon kodi allaqachon mavjud."}, status=status.HTTP_400_BAD_REQUEST)

        # Sozlamalarni olish
        settings = ReferralAndCouponSettings.objects.last()
        if not settings:
            return Response({"error": "Kupon sozlamalari mavjud emas."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Amal qilish muddati
        valid_until = timezone.now() + timedelta(days=settings.coupon_valid_days)

        # Kupon yaratamiz
        coupon = Coupon.objects.create(
            code=code,
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

