from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import BasePermission
from django_app.app_management.models import SystemSettings
from django_app.app_management.serializers import SystemSettingsSerializer


class SystemSettingsCRUDAPIView(APIView):

    # 🔐 Faqat SuperAdmin uchun ruxsat
    class IsSuperAdmin(BasePermission):
        def has_permission(self, request, view):
            return (
                request.user.is_authenticated and
                getattr(request.user, "role", None) == "superadmin"
            )

    permission_classes = [IsSuperAdmin]

    # 📌 GET — list yoki detail
    def get(self, request, pk=None):
        if pk:
            try:
                settings_obj = SystemSettings.objects.get(pk=pk)
            except SystemSettings.DoesNotExist:
                return Response({"error": "System settings topilmadi"}, status=404)

            serializer = SystemSettingsSerializer(settings_obj)
            return Response(serializer.data)

        settings_list = SystemSettings.objects.all()
        serializer = SystemSettingsSerializer(settings_list, many=True)
        return Response(serializer.data)

    # 📌 CREATE
    def post(self, request):
        serializer = SystemSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "System sozlamalari yaratildi", "data": serializer.data},
            status=status.HTTP_201_CREATED
        )

    # 📌 UPDATE — logo, file va textlar bilan
    def put(self, request, pk):
        try:
            settings_obj = SystemSettings.objects.get(pk=pk)
        except SystemSettings.DoesNotExist:
            return Response({"error": "System settings topilmadi"}, status=404)

        serializer = SystemSettingsSerializer(settings_obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "System sozlamalari yangilandi", "data": serializer.data},
            status=200
        )

    # 📌 DELETE
    def delete(self, request, pk):
        try:
            settings_obj = SystemSettings.objects.get(pk=pk)
        except SystemSettings.DoesNotExist:
            return Response({"error": "System settings topilmadi"}, status=404)

        settings_obj.delete()

        return Response({"message": "System sozlamalari o‘chirildi"}, status=204)
