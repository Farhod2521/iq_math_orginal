from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import BasePermission
from django_app.app_management.models import UploadSetting
from django_app.app_management.serializers import UploadSettingSerializer


class IsTeacherOrSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            getattr(request.user, "role", None) in ["teacher", "superadmin"]
        )


class UploadSettingCRUDAPIView(APIView):
    permission_classes = [IsTeacherOrSuperAdmin]

    # GET — list yoki detail
    def get(self, request, pk=None):
        if pk:
            try:
                obj = UploadSetting.objects.get(pk=pk)
            except UploadSetting.DoesNotExist:
                return Response({"error": "UploadSetting topilmadi."}, status=404)
            return Response(UploadSettingSerializer(obj).data)

        queryset = UploadSetting.objects.all()
        return Response(UploadSettingSerializer(queryset, many=True).data)

    # POST — yaratish
    def post(self, request):
        serializer = UploadSettingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Yuklash sozlamasi yaratildi.", "data": serializer.data},
            status=status.HTTP_201_CREATED
        )

    # PUT — yangilash (partial)
    def put(self, request, pk):
        try:
            obj = UploadSetting.objects.get(pk=pk)
        except UploadSetting.DoesNotExist:
            return Response({"error": "UploadSetting topilmadi."}, status=404)

        serializer = UploadSettingSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Yuklash sozlamasi yangilandi.", "data": serializer.data},
            status=status.HTTP_200_OK
        )

    # DELETE — o'chirish
    def delete(self, request, pk):
        try:
            obj = UploadSetting.objects.get(pk=pk)
        except UploadSetting.DoesNotExist:
            return Response({"error": "UploadSetting topilmadi."}, status=404)

        obj.delete()
        return Response({"message": "Yuklash sozlamasi o'chirildi."}, status=status.HTTP_204_NO_CONTENT)
