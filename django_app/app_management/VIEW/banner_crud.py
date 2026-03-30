from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import BasePermission
from django_app.app_management.models import Banner
from django_app.app_management.serializers import BannerSerializer
import os


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            getattr(request.user, "role", None) in ["superadmin", "admin"]
        )


class BannerCRUDAPIView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request, pk=None):
        if pk:
            try:
                obj = Banner.objects.get(pk=pk)
            except Banner.DoesNotExist:
                return Response({"error": "Banner topilmadi."}, status=404)
            return Response(BannerSerializer(obj, context={"request": request}).data)

        queryset = Banner.objects.all()
        return Response(BannerSerializer(queryset, many=True, context={"request": request}).data)

    def post(self, request):
        serializer = BannerSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return Response(
            {"message": "Banner yaratildi.", "data": BannerSerializer(obj, context={"request": request}).data},
            status=status.HTTP_201_CREATED
        )

    def put(self, request, pk):
        try:
            obj = Banner.objects.get(pk=pk)
        except Banner.DoesNotExist:
            return Response({"error": "Banner topilmadi."}, status=404)

        # Yangi rasm kelsa eskisini o'chiramiz
        old_image = obj.image
        serializer = BannerSerializer(obj, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)

        if "image" in request.data and old_image:
            if os.path.isfile(old_image.path):
                os.remove(old_image.path)

        obj = serializer.save()
        return Response(
            {"message": "Banner yangilandi.", "data": BannerSerializer(obj, context={"request": request}).data}
        )

    def delete(self, request, pk):
        try:
            obj = Banner.objects.get(pk=pk)
        except Banner.DoesNotExist:
            return Response({"error": "Banner topilmadi."}, status=404)

        # Rasmni ham o'chiramiz
        if obj.image and os.path.isfile(obj.image.path):
            os.remove(obj.image.path)

        obj.delete()
        return Response({"message": "Banner o'chirildi."}, status=status.HTTP_204_NO_CONTENT)
