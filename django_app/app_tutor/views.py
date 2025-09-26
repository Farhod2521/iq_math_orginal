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

        # ❗️context berish
        serializer = CouponCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        valid_from = timezone.now()
        valid_until = valid_from + timedelta(days=settings.coupon_valid_days)

        # validated_data ichida already created_by_tutor bor
        coupon = serializer.save(
            discount_percent=settings.coupon_discount_percent,
            valid_from=valid_from,
            valid_until=valid_until,
            is_active=True
        )

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
        try:
            settings = ReferralAndCouponSettings.objects.latest('updated_at')
        except ReferralAndCouponSettings.DoesNotExist:
            return Response({"error": "ReferralAndCouponSettings topilmadi"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ReferralCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        valid_from = timezone.now()
        valid_until = valid_from + timedelta(days=settings.referral_valid_days)

        referral = serializer.save(
            bonus_percent=settings.referral_bonus_coin,
            valid_from=valid_from,
            valid_until=valid_until,
            is_active=True
        )

        return Response({
            "message": "Referal link muvaffaqiyatli yaratildi",
            "referral": {
                "code": referral.code,
                "bonus_percent": referral.bonus_percent,
                "valid_from": referral.valid_from,
                "valid_until": referral.valid_until
            }
        }, status=status.HTTP_201_CREATED)
