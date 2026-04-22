from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from django_app.app_management.models import SystemSettings
from django_app.app_management.permissions import IsTeacherOrSuperAdmin
from django_app.app_management.serializers import SystemSettingsSerializer


class SystemSettingsCRUDAPIView(APIView):
    """
    Singleton model - tizimda faqat 1 ta SystemSettings yozuvi bo'ladi.

    GET    /api/v1/management/system-settings/ -> joriy sozlamani olish
    POST   /api/v1/management/system-settings/ -> birinchi marta yaratish
    PUT    /api/v1/management/system-settings/ -> mavjud sozlamani yangilash
    DELETE /api/v1/management/system-settings/ -> mavjud sozlamani o'chirish
    """

    permission_classes = [IsTeacherOrSuperAdmin]

    def _get_settings(self):
        return SystemSettings.objects.order_by("id").last()

    def get(self, request):
        settings_obj = self._get_settings()
        if not settings_obj:
            return Response(
                {"error": "System sozlamalari hali yaratilmagan."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = SystemSettingsSerializer(settings_obj)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if SystemSettings.objects.exists():
            return Response(
                {
                    "error": (
                        "System sozlamalari allaqachon mavjud. "
                        "Yangilash uchun PUT dan foydalaning."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SystemSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "System sozlamalari yaratildi.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    def put(self, request):
        settings_obj = self._get_settings()
        if not settings_obj:
            return Response(
                {"error": "System sozlamalari topilmadi. Avval POST orqali yarating."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = SystemSettingsSerializer(
            settings_obj,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "System sozlamalari yangilandi.", "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    def delete(self, request):
        settings_obj = self._get_settings()
        if not settings_obj:
            return Response(
                {"error": "System sozlamalari topilmadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        SystemSettings.objects.all().delete()
        return Response(
            {"message": "System sozlamalari o'chirildi."},
            status=status.HTTP_200_OK,
        )
