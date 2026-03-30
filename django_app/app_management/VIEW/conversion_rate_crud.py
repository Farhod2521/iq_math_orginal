from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import BasePermission
from django_app.app_management.models import ConversionRate


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            getattr(request.user, "role", None) in ["superadmin", "admin"]
        )


class ConversionRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversionRate
        fields = ["id", "coin_to_score", "coin_to_money", "updated_at"]
        read_only_fields = ["id", "updated_at"]


class ConversionRateCRUDAPIView(APIView):
    """
    Singleton model — tizimda faqat 1 ta yozuv bo'ladi.
    GET  /api/v1/management/superadmin/conversion-rate/        → joriy kursni olish
    POST /api/v1/management/superadmin/conversion-rate/        → yaratish (birinchi marta)
    PUT  /api/v1/management/superadmin/conversion-rate/        → yangilash (pk shart emas)
    """
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        obj = ConversionRate.objects.last()
        if not obj:
            return Response({"detail": "Konversiya kursi hali sozlanmagan."}, status=404)
        return Response(ConversionRateSerializer(obj).data)

    def post(self, request):
        if ConversionRate.objects.exists():
            return Response(
                {"error": "Konversiya kursi allaqachon mavjud. Yangilash uchun PUT dan foydalaning."},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = ConversionRateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Konversiya kursi yaratildi.", "data": serializer.data},
            status=status.HTTP_201_CREATED
        )

    def put(self, request):
        obj = ConversionRate.objects.last()
        if not obj:
            return Response({"error": "Avval POST orqali yarating."}, status=404)
        serializer = ConversionRateSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Konversiya kursi yangilandi.", "data": serializer.data}
        )
