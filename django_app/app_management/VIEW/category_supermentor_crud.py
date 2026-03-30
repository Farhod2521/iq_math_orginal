from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import BasePermission
from django_app.app_management.models import Category
from django_app.app_management.serializers import CategorySerializer


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            getattr(request.user, "role", None) in ["superadmin", "admin"]
        )


class CategoryCRUDAPIView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request, pk=None):
        if pk:
            try:
                obj = Category.objects.get(pk=pk)
            except Category.DoesNotExist:
                return Response({"error": "Kategoriya topilmadi."}, status=404)
            return Response(CategorySerializer(obj).data)

        queryset = Category.objects.all()
        return Response(CategorySerializer(queryset, many=True).data)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Kategoriya yaratildi.", "data": serializer.data},
            status=status.HTTP_201_CREATED
        )

    def put(self, request, pk):
        try:
            obj = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return Response({"error": "Kategoriya topilmadi."}, status=404)

        serializer = CategorySerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Kategoriya yangilandi.", "data": serializer.data}
        )

    def delete(self, request, pk):
        try:
            obj = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return Response({"error": "Kategoriya topilmadi."}, status=404)

        obj.delete()
        return Response({"message": "Kategoriya o'chirildi."}, status=status.HTTP_204_NO_CONTENT)
