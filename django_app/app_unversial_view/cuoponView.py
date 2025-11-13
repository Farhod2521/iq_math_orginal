from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, permissions, status
import random
import string
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum
from django_app.app_management.models import Coupon_Tutor_Student, ReferralAndCouponSettings
from .cuoponSerizalizer import  CouponCreateSerializer, CouponSerializer




class UniversalCouponViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CouponSerializer
    queryset = Coupon_Tutor_Student.objects.all()

    def _generate_unique_coupon_code(self, length=6):
        chars = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(random.choices(chars, k=length))
            if not Coupon_Tutor_Student.objects.filter(code=code).exists():
                return code

    def get_queryset(self):
        """Foydalanuvchi faqat o‘zi yaratgan kuponlarni ko‘radi"""
        user = self.request.user

        if user.role == 'student':
            student = user.student_profile
            return Coupon_Tutor_Student.objects.filter(created_by_student=student)

        elif user.role == 'tutor':
            tutor = user.tutor_profile
            return Coupon_Tutor_Student.objects.filter(created_by_tutor=tutor)

        elif user.role == 'teacher':
            teacher = user.teacher_profile
            return Coupon_Tutor_Student.objects.filter(created_by_teacher=teacher)

        return Coupon_Tutor_Student.objects.none()

    def create(self, request, *args, **kwargs):

        # --- SETTINGS ---
        try:
            settings = ReferralAndCouponSettings.objects.latest('updated_at')
        except ReferralAndCouponSettings.DoesNotExist:
            return Response({"error": "ReferralAndCouponSettings topilmadi"},
                            status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        role = user.role  # student / tutor / teacher

        valid_from = timezone.now()
        valid_until = valid_from + timedelta(days=settings.coupon_valid_days)
        coupon_code = self._generate_unique_coupon_code()

        existing_coupon = None

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

        # --- Agar mavjud bo‘lsa, qaytaramiz ---
        if existing_coupon:
            return Response({
                "message": "Siz allaqachon kupon yaratgansiz",
                "coupon": CouponSerializer(existing_coupon).data
            }, status=status.HTTP_200_OK)

        # --- Yangi kupon yaratish ---
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
