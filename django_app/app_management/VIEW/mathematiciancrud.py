from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import BasePermission
from django_app.app_management.models import Mathematician


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            getattr(request.user, "role", None) in ["superadmin", "admin"]
        )


class MathematicianWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mathematician
        fields = [
            "title_uz", "title_ru",
            "subtitle_uz", "subtitle_ru",
            "life_years_uz", "life_years_ru",
            "description_uz", "description_ru",
            "image", "is_active",
        ]


class MathematicianReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mathematician
        fields = [
            "id",
            "title_uz", "title_ru",
            "subtitle_uz", "subtitle_ru",
            "life_years_uz", "life_years_ru",
            "description_uz", "description_ru",
            "image", "is_active", "created_at",
        ]


class MathematicianCRUDAPIView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request, pk=None):
        if pk:
            try:
                obj = Mathematician.objects.get(pk=pk)
            except Mathematician.DoesNotExist:
                return Response({"error": "Matematik olim topilmadi."}, status=404)
            return Response(MathematicianReadSerializer(obj, context={"request": request}).data)

        queryset = Mathematician.objects.all()
        return Response(MathematicianReadSerializer(queryset, many=True, context={"request": request}).data)

    def post(self, request):
        serializer = MathematicianWriteSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return Response(
            {"message": "Matematik olim yaratildi.", "data": MathematicianReadSerializer(obj, context={"request": request}).data},
            status=status.HTTP_201_CREATED
        )

    def put(self, request, pk):
        try:
            obj = Mathematician.objects.get(pk=pk)
        except Mathematician.DoesNotExist:
            return Response({"error": "Matematik olim topilmadi."}, status=404)

        serializer = MathematicianWriteSerializer(obj, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return Response(
            {"message": "Matematik olim yangilandi.", "data": MathematicianReadSerializer(obj, context={"request": request}).data}
        )

    def delete(self, request, pk):
        try:
            obj = Mathematician.objects.get(pk=pk)
        except Mathematician.DoesNotExist:
            return Response({"error": "Matematik olim topilmadi."}, status=404)

        obj.delete()
        return Response({"message": "Matematik olim o'chirildi."}, status=status.HTTP_204_NO_CONTENT)
