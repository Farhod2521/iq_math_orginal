from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.utils import timezone
from datetime import timedelta
from django_app.app_management.models import  Coupon_Tutor_Student, ReferralAndCouponSettings, Referral_Tutor_Student
from .serializers import CouponCreateSerializer, ReferralCreateSerializer
from django.db import IntegrityError

class TutorCreateCouponAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            settings = ReferralAndCouponSettings.objects.latest('updated_at')
        except ReferralAndCouponSettings.DoesNotExist:
            return Response({"error": "ReferralAndCouponSettings topilmadi"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CouponCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tutor = getattr(request.user, 'tutor', None)
        if tutor is None:
            return Response({"error": "Foydalanuvchi O'qtuvchi emas"}, status=status.HTTP_403_FORBIDDEN)

        valid_from = timezone.now()
        valid_until = valid_from + timedelta(days=settings.coupon_valid_days)

        try:
            coupon = Coupon_Tutor_Student.objects.create(
                code=serializer.validated_data['code'],
                discount_percent=settings.coupon_discount_percent,
                valid_from=valid_from,
                valid_until=valid_until,
                created_by_tutor=tutor,
                is_active=True
            )
        except IntegrityError:
            return Response({"error": "Bu kupon kodi allaqachon mavjud"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": "Kupon muvaffaqiyatli yaratildi",
            "coupon": {
                "code": coupon.code,
                "discount_percent": coupon.discount_percent,
                "valid_from": coupon.valid_from,
                "valid_until": coupon.valid_until
            }
        }, status=status.HTTP_201_CREATED)
    


class TutorCreateReferralAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # sozlamalarni olish
        try:
            settings = ReferralAndCouponSettings.objects.latest('updated_at')
        except ReferralAndCouponSettings.DoesNotExist:
            return Response({"error": "ReferralAndCouponSettings topilmadi"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ReferralCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tutor = getattr(request.user, 'tutor_profile', None)
        if tutor is None:
            return Response({"error": "Foydalanuvchi O‘qituvchi emas"}, status=status.HTTP_403_FORBIDDEN)

        valid_from = timezone.now()
        valid_until = valid_from + timedelta(days=settings.referral_valid_days)

        try:
            referral = Referral_Tutor_Student.objects.create(
                code=serializer.validated_data['code'],
                bonus_percent=settings.referral_bonus_coin,
                valid_from=valid_from,
                valid_until=valid_until,
                created_by_tutor=tutor,
                is_active=True
            )
        except IntegrityError:
            return Response({"error": "Bu referal kodi allaqachon mavjud"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": "Referal link muvaffaqiyatli yaratildi",
            "referral": {
                "code": referral.code,
                "bonus_percent": referral.bonus_percent,
                "valid_from": referral.valid_from,
                "valid_until": referral.valid_until
            }
        }, status=status.HTTP_201_CREATED)