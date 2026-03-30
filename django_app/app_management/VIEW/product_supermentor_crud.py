from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import BasePermission
from django_app.app_management.models import Product
from django_app.app_management.serializers import ProductSerializer


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            getattr(request.user, "role", None) in ["superadmin", "admin"]
        )


class ProductWriteSerializer(serializers.ModelSerializer):
    """POST / PUT uchun — faqat yoziladigan maydonlar"""
    class Meta:
        model = Product
        fields = ["name_uz", "name_ru", "coin", "count", "image"]


class ProductCRUDAPIView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request, pk=None):
        if pk:
            try:
                obj = Product.objects.get(pk=pk)
            except Product.DoesNotExist:
                return Response({"error": "Mahsulot topilmadi."}, status=404)
            return Response(ProductSerializer(obj, context={"request": request}).data)

        queryset = Product.objects.all()
        return Response(ProductSerializer(queryset, many=True, context={"request": request}).data)

    def post(self, request):
        serializer = ProductWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(
            {"message": "Mahsulot yaratildi.", "data": ProductSerializer(product, context={"request": request}).data},
            status=status.HTTP_201_CREATED
        )

    def put(self, request, pk):
        try:
            obj = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({"error": "Mahsulot topilmadi."}, status=404)

        serializer = ProductWriteSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(
            {"message": "Mahsulot yangilandi.", "data": ProductSerializer(product, context={"request": request}).data}
        )

    def delete(self, request, pk):
        try:
            obj = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({"error": "Mahsulot topilmadi."}, status=404)

        obj.delete()
        return Response({"message": "Mahsulot o'chirildi."}, status=status.HTTP_204_NO_CONTENT)
