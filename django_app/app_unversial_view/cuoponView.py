from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
import random
import string
from django.utils import timezone
from datetime import timedelta

from django_app.app_management.models import Coupon_Tutor_Student, ReferralAndCouponSettings
from .cuoponSerizalizer import CouponCreateSerializer, CouponSerializer


class UniversalCouponAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    # --- Unique kupon generatsiya qilish ---
    def _generate_unique_coupon_code(self, length=6):
        chars = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(random.choices(chars, k=length))
            if not Coupon_Tutor_Student.objects.filter(code=code).exists():
                return code

    # --- GET: Foydalanuvchining kuponini qaytaradi ---
    def get(self, request):
        user = request.user
        role = user.role

        coupon = None

        if role == 'student':
            coupon = Coupon_Tutor_Student.objects.filter(created_by_student=user.student_profile).first()

        elif role == 'tutor':
            coupon = Coupon_Tutor_Student.objects.filter(created_by_tutor=user.tutor_profile).first()

        elif role == 'teacher':
            coupon = Coupon_Tutor_Student.objects.filter(created_by_teacher=user.teacher_profile).first()

        else:
            raise PermissionDenied("Role uchun ruxsat yo‘q!")

        if coupon is None:
            return Response({"message": "Siz hali kupon yaratmagansiz."}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "message": "Sizning kuponingiz:",
            "coupon": CouponSerializer(coupon).data
        }, status=status.HTTP_200_OK)

    # --- POST: Yangi kupon yaratish ---
    def post(self, request):
        user = request.user
        role = user.role

        # SETTINGS
        try:
            settings = ReferralAndCouponSettings.objects.latest('updated_at')
        except ReferralAndCouponSettings.DoesNotExist:
            return Response({"error": "ReferralAndCouponSettings topilmadi"},
                            status=status.HTTP_400_BAD_REQUEST)

        # Kupon muddati
        valid_from = timezone.now()
        valid_until = valid_from + timedelta(days=settings.coupon_valid_days)

        existing_coupon = None
        creator_data = {}

        # --- STUDENT ---
        if role == 'student':
            student = user.student_profile
            existing_coupon = Coupon_Tutor_Student.objects.filter(created_by_student=student).first()
            creator_data = {"created_by_student": student}

        # --- TUTOR ---
        elif role == 'tutor':
            tutor = user.tutor_profile
            existing_coupon = Coupon_Tutor_Student.objects.filter(created_by_tutor=tutor).first()
            creator_data = {"created_by_tutor": tutor}

        # --- TEACHER ---
        elif role == 'teacher':
            teacher = user.teacher_profile
            existing_coupon = Coupon_Tutor_Student.objects.filter(created_by_teacher=teacher).first()
            creator_data = {"created_by_teacher": teacher}

        else:
            raise PermissionDenied("Role uchun ruxsat yo‘q!")

        # Agar bor bo‘lsa — mavjudini qaytarish
        if existing_coupon:
            return Response({
                "message": "Siz allaqachon kupon yaratgansiz",
                "coupon": CouponSerializer(existing_coupon).data
            }, status=status.HTTP_200_OK)

        # Yangi kupon kodi
        coupon_code = self._generate_unique_coupon_code()

        serializer = CouponCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        coupon = serializer.save(
            code=coupon_code,
            discount_percent=settings.coupon_discount_percent,
            valid_from=valid_from,
            valid_until=valid_until,
            is_active=True,
            **creator_data
        )

        return Response({
            "message": "Kupon muvaffaqiyatli yaratildi",
            "coupon": CouponSerializer(coupon).data
        }, status=status.HTTP_201_CREATED)
