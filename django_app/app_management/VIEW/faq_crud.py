from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import BasePermission
from django_app.app_management.models import FAQ
from django_app.app_management.serializers import FAQSerializer


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            getattr(request.user, "role", None) in ["superadmin", "admin"]
        )


class FAQCRUDAPIView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request, pk=None):
        if pk:
            try:
                obj = FAQ.objects.get(pk=pk)
            except FAQ.DoesNotExist:
                return Response({"error": "FAQ topilmadi."}, status=404)
            return Response(FAQSerializer(obj).data)

        queryset = FAQ.objects.all()
        return Response(FAQSerializer(queryset, many=True).data)

    def post(self, request):
        serializer = FAQSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return Response(
            {"message": "FAQ yaratildi.", "data": FAQSerializer(obj).data},
            status=status.HTTP_201_CREATED
        )

    def put(self, request, pk):
        try:
            obj = FAQ.objects.get(pk=pk)
        except FAQ.DoesNotExist:
            return Response({"error": "FAQ topilmadi."}, status=404)

        serializer = FAQSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return Response(
            {"message": "FAQ yangilandi.", "data": FAQSerializer(obj).data}
        )

    def delete(self, request, pk):
        try:
            obj = FAQ.objects.get(pk=pk)
        except FAQ.DoesNotExist:
            return Response({"error": "FAQ topilmadi."}, status=404)

        obj.delete()
        return Response({"message": "FAQ o'chirildi."}, status=status.HTTP_204_NO_CONTENT)
