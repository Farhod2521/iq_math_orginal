from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import BasePermission
from django_app.app_management.models import Tag
from django_app.app_management.serializers import TagSerializer


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            getattr(request.user, "role", None) in ["superadmin", "admin"]
        )


class TagCRUDAPIView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request, pk=None):
        if pk:
            try:
                obj = Tag.objects.get(pk=pk)
            except Tag.DoesNotExist:
                return Response({"error": "Teg topilmadi."}, status=404)
            return Response(TagSerializer(obj).data)

        queryset = Tag.objects.all()
        return Response(TagSerializer(queryset, many=True).data)

    def post(self, request):
        serializer = TagSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return Response(
            {"message": "Teg yaratildi.", "data": TagSerializer(obj).data},
            status=status.HTTP_201_CREATED
        )

    def put(self, request, pk):
        try:
            obj = Tag.objects.get(pk=pk)
        except Tag.DoesNotExist:
            return Response({"error": "Teg topilmadi."}, status=404)

        serializer = TagSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return Response(
            {"message": "Teg yangilandi.", "data": TagSerializer(obj).data}
        )

    def delete(self, request, pk):
        try:
            obj = Tag.objects.get(pk=pk)
        except Tag.DoesNotExist:
            return Response({"error": "Teg topilmadi."}, status=404)

        obj.delete()
        return Response({"message": "Teg o'chirildi."}, status=status.HTTP_204_NO_CONTENT)
