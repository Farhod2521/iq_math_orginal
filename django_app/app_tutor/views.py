from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.utils import timezone
from datetime import timedelta
from django_app.app_management.models import  Coupon, ReferralAndCouponSettings
from .serializers import CouponCreateSerializer


class TutorCreateCouponAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # faqat login bo‘lganlar

    def post(self, request, *args, **kwargs):
        # 1️⃣ – Sozlamalarni olish
        try:
            settings = ReferralAndCouponSettings.objects.latest('updated_at')
        except ReferralAndCouponSettings.DoesNotExist:
            return Response({"error": "ReferralAndCouponSettings topilmadi"}, status=status.HTTP_400_BAD_REQUEST)

        # 2️⃣ – Serializer orqali code ni olish
        serializer = CouponCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 3️⃣ – current tutor (request.user) dan Tutor obyektini olish
        tutor = getattr(request.user, 'tutor', None)
        if tutor is None:
            return Response({"error": "Foydalanuvchi O'qtuvchi emas"}, status=status.HTTP_403_FORBIDDEN)

        # 4️⃣ – valid_until ni hisoblash
        valid_from = timezone.now()
        valid_until = valid_from + timedelta(days=settings.coupon_valid_days)

        # 5️⃣ – Coupon yaratish
        coupon = Coupon.objects.create(
            code=serializer.validated_data['code'],
            discount_percent=settings.coupon_discount_percent,
            valid_from=valid_from,
            valid_until=valid_until,
            created_by_tutor=tutor,
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
