from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone
from datetime import timedelta

from django_app.app_user.models import Teacher
from django_app.app_management.models import Coupon, ReferralAndCouponSettings
from django_app.app_teacher.models import TeacherCouponTransaction

class CreateTeacherCouponAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # Foydalanuvchi teacher ekanini tekshiramiz
        try:
            teacher = user.teacher_profile
        except Teacher.DoesNotExist:
            return Response({
                "error_uz": "O‘qituvchi profili mavjud emas.",
                "error_ru": "Профиль преподавателя не найден."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Kupon kodi yuborilganmi?
        code = request.data.get("code")
        if not code:
            return Response({
                "error_uz": "Kupon kodi kiritilmadi.",
                "error_ru": "Код купона не был введен."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Takrorlanmaganligini tekshiramiz
        if Coupon.objects.filter(code=code).exists():
            return Response({
                "error_uz": "Bu kupon kodi allaqachon mavjud.",
                "error_ru": "Этот код купона уже существует."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Sozlamalarni olish
        settings = ReferralAndCouponSettings.objects.last()
        if not settings:
            return Response({
                "error_uz": "Kupon sozlamalari mavjud emas.",
                "error_ru": "Настройки купона не найдены."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
            "message_uz": "Kupon muvaffaqiyatli yaratildi.",
            "message_ru": "Купон успешно создан.",
            "coupon_code": coupon.code,
            "discount_percent": coupon.discount_percent,
            "valid_until": coupon.valid_until
        }, status=status.HTTP_201_CREATED)


class TeacherCouponStudentsAPIView(APIView):
    """
    O'qituvchining promokodini ishlatgan o'quvchilar ro'yxati
    GET /api/v1/func_teacher/teacher/coupon-students/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        try:
            teacher = user.teacher_profile
        except Teacher.DoesNotExist:
            return Response({
                "error_uz": "O'qituvchi profili mavjud emas.",
                "error_ru": "Профиль преподавателя не найден."
            }, status=status.HTTP_400_BAD_REQUEST)

        transactions = TeacherCouponTransaction.objects.filter(
            teacher=teacher
        ).select_related('student', 'coupon').order_by('-used_at')

        data = []
        for tx in transactions:
            student = tx.student
            data.append({
                "student_id": student.id,
                "student_identification": student.identification,
                "student_full_name": student.full_name,
                "coupon_code": tx.coupon.code,
                "discount_percent": tx.coupon.discount_percent,
                "payment_amount": tx.payment_amount,
                "used_at": tx.used_at,
            })

        return Response(data, status=status.HTTP_200_OK)
