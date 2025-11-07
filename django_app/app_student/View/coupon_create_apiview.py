from rest_framework import viewsets, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from datetime import timedelta
from django.utils import timezone
import string, random
from django_app.app_management.models import Coupon_Tutor_Student, ReferralAndCouponSettings
from django_app.app_student.serializers import  StudentCouponCreateSerializer, CouponSerializer
class StudentCouponViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CouponSerializer  # Xuddi Tutor uchun bo‘lgani kabi

    def get_queryset(self):
        student = getattr(self.request.user, 'student_profile', None)
        if student is None:
            raise PermissionDenied("Foydalanuvchi o‘quvchi emas")
        return Coupon_Tutor_Student.objects.filter(created_by_student=student)

    def _generate_unique_coupon_code(self, length=6):
        """A-Z va 0-9 dan iborat unikal kupon kodi yaratish."""
        chars = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(random.choices(chars, k=length))
            if not Coupon_Tutor_Student.objects.filter(code=code).exists():
                return code

    def create(self, request, *args, **kwargs):
        try:
            settings = ReferralAndCouponSettings.objects.latest('updated_at')
        except ReferralAndCouponSettings.DoesNotExist:
            return Response({"error": "ReferralAndCouponSettings topilmadi"},
                            status=status.HTTP_400_BAD_REQUEST)

        student = getattr(request.user, 'student_profile', None)
        if student is None:
            raise PermissionDenied("Foydalanuvchi o‘quvchi emas")

        # 🔹 Agar student allaqachon kupon yaratgan bo‘lsa — shuni qaytaramiz
        existing_coupon = Coupon_Tutor_Student.objects.filter(created_by_student=student).first()
        if existing_coupon:
            return Response({
                "message": "Siz allaqachon kupon yaratgansiz",
                "coupon": CouponSerializer(existing_coupon).data
            }, status=status.HTTP_200_OK)

        # 🔹 Yangi kupon uchun muddat va kod yaratish
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

        return Response(CouponSerializer(coupon).data, status=status.HTTP_201_CREATED)
