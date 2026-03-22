from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import BasePermission
from django_app.app_management.models import DailyCoinSettings
from django_app.app_management.serializers import DailyCoinSettingsSerializer


class IsTeacherOrSuperAdmin(BasePermission):
    """Faqat teacher va superadmin rollari kirishi mumkin"""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            getattr(request.user, "role", None) in ["teacher", "superadmin"]
        )


class DailyCoinSettingsCRUDAPIView(APIView):
    permission_classes = [IsTeacherOrSuperAdmin]

    # 📌 GET — list yoki detail
    def get(self, request, pk=None):
        if pk:
            try:
                obj = DailyCoinSettings.objects.get(pk=pk)
            except DailyCoinSettings.DoesNotExist:
                return Response({"error": "DailyCoinSettings topilmadi."}, status=404)
            serializer = DailyCoinSettingsSerializer(obj)
            return Response(serializer.data)

        queryset = DailyCoinSettings.objects.all()
        serializer = DailyCoinSettingsSerializer(queryset, many=True)
        return Response(serializer.data)

    # 📌 POST — yaratish
    def post(self, request):
        serializer = DailyCoinSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Kunlik tanga sozlamasi yaratildi.", "data": serializer.data},
            status=status.HTTP_201_CREATED
        )

    # 📌 PUT — yangilash (partial)
    def put(self, request, pk):
        try:
            obj = DailyCoinSettings.objects.get(pk=pk)
        except DailyCoinSettings.DoesNotExist:
            return Response({"error": "DailyCoinSettings topilmadi."}, status=404)

        serializer = DailyCoinSettingsSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Kunlik tanga sozlamasi yangilandi.", "data": serializer.data},
            status=status.HTTP_200_OK
        )

    # 📌 DELETE — o'chirish
    def delete(self, request, pk):
        try:
            obj = DailyCoinSettings.objects.get(pk=pk)
        except DailyCoinSettings.DoesNotExist:
            return Response({"error": "DailyCoinSettings topilmadi."}, status=404)

        obj.delete()
        return Response({"message": "Kunlik tanga sozlamasi o'chirildi."}, status=status.HTTP_204_NO_CONTENT)
