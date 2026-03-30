from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import BasePermission
from django_app.app_management.models import ReferralAndCouponSettings


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            getattr(request.user, "role", None) in ["superadmin", "admin"]
        )


class ReferralAndCouponSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralAndCouponSettings
        fields = [
            "id",
            "teacher_referral_bonus_points",
            "student_referral_bonus_points",
            "coupon_discount_percent",
            "coupon_discount_percent_teacher",
            "coupon_valid_days",
            "referral_valid_days",
            "coupon_student_cashback_percent",
            "coupon_teacher_cashback_percent",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ReferralCouponSettingsCRUDAPIView(APIView):
    """
    Singleton model — tizimda faqat 1 ta yozuv bo'ladi.
    GET  /api/v1/management/superadmin/referral-coupon-settings/   → joriy sozlamani olish
    POST /api/v1/management/superadmin/referral-coupon-settings/   → birinchi marta yaratish
    PUT  /api/v1/management/superadmin/referral-coupon-settings/   → yangilash
    """
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        obj = ReferralAndCouponSettings.objects.last()
        if not obj:
            return Response({"detail": "Sozlama hali yaratilmagan."}, status=404)
        return Response(ReferralAndCouponSettingsSerializer(obj).data)

    def post(self, request):
        if ReferralAndCouponSettings.objects.exists():
            return Response(
                {"error": "Sozlama allaqachon mavjud. Yangilash uchun PUT dan foydalaning."},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = ReferralAndCouponSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Sozlama yaratildi.", "data": serializer.data},
            status=status.HTTP_201_CREATED
        )

    def put(self, request):
        obj = ReferralAndCouponSettings.objects.last()
        if not obj:
            return Response({"error": "Avval POST orqali yarating."}, status=404)
        serializer = ReferralAndCouponSettingsSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Sozlama yangilandi.", "data": serializer.data}
        )
