from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from datetime import timedelta
import string, random
from django_app.app_management.models import Coupon_Tutor_Student, ReferralAndCouponSettings
from django_app.app_student.serializers import  StudentCouponCreateSerializer, CouponSerializer


class StudentCouponAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _generate_unique_coupon_code(self, length=6):
        """A-Z va 0-9 dan iborat unikal kupon kodi yaratish."""
        chars = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(random.choices(chars, k=length))
            if not Coupon_Tutor_Student.objects.filter(code=code).exists():
                return code

    def get(self, request):
        """🔹 Foydalanuvchining mavjud kuponini qaytaradi"""
        student = getattr(request.user, 'student_profile', None)
        if student is None:
            raise PermissionDenied("Foydalanuvchi o‘quvchi emas")

        coupon = Coupon_Tutor_Student.objects.filter(created_by_student=student).first()
        if not coupon:
            return Response({"message": "Siz hali kupon yaratmagansiz."}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "message": "Sizning kuponingiz:",
            "coupon": CouponSerializer(coupon).data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        """🔹 Student uchun yangi kupon yaratadi (agar allaqachon bo‘lmasa)"""
        student = getattr(request.user, 'student_profile', None)
        if student is None:
            raise PermissionDenied("Foydalanuvchi o‘quvchi emas")

        try:
            settings = ReferralAndCouponSettings.objects.latest('updated_at')
        except ReferralAndCouponSettings.DoesNotExist:
            return Response(
                {"error": "ReferralAndCouponSettings topilmadi"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 🔸 Agar student allaqachon kupon yaratgan bo‘lsa — shuni qaytaramiz
        existing_coupon = Coupon_Tutor_Student.objects.filter(created_by_student=student).first()
        if existing_coupon:
            return Response({
                "message": "Siz allaqachon kupon yaratgansiz",
                "coupon": CouponSerializer(existing_coupon).data
            }, status=status.HTTP_200_OK)

        # 🔸 Yangi kupon ma’lumotlari
        valid_from = timezone.now()
        valid_until = valid_from + timedelta(days=settings.coupon_valid_days)
        coupon_code = self._generate_unique_coupon_code()

        serializer = StudentCouponCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        coupon = serializer.save(
            code=coupon_code,
            discount_percent=settings.coupon_discount_percent,
            valid_from=valid_from,
            valid_until=valid_until,
            created_by_student=student,
            is_active=True
        )

        return Response({
            "message": "Kupon muvaffaqiyatli yaratildi",
            "coupon": CouponSerializer(coupon).data
        }, status=status.HTTP_201_CREATED)