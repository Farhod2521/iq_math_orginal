from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import BasePermission
from django_app.app_management.models import Motivation
from django_app.app_management.serializers import MotivationSerializer


class MotivationCRUDAPIView(APIView):

    # ✅ FAQAT SUPERADMIN UCHUN PERMISSION (VIEW ICHIDA)
    class IsSuperAdmin(BasePermission):
        def has_permission(self, request, view):
            return (
                request.user.is_authenticated and
                getattr(request.user, "role", None) == "superadmin"
            )

    permission_classes = [IsSuperAdmin]

    # ✅ GET — LIST yoki DETAIL
    def get(self, request, pk=None):
        if pk:
            try:
                motivation = Motivation.objects.get(pk=pk)
            except Motivation.DoesNotExist:
                return Response({"error": "Motivatsion matn topilmadi"}, status=404)

            serializer = MotivationSerializer(motivation)
            return Response(serializer.data)

        motivations = Motivation.objects.all().order_by("-created_at")
        serializer = MotivationSerializer(motivations, many=True)
        return Response(serializer.data)

    # ✅ CREATE
    def post(self, request):
        serializer = MotivationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "message": "Motivatsion matn yaratildi",
                "data": serializer.data
            },
            status=status.HTTP_201_CREATED
        )

    # ✅ UPDATE (to‘liq yoki qisman)
    def put(self, request, pk):
        try:
            motivation = Motivation.objects.get(pk=pk)
        except Motivation.DoesNotExist:
            return Response({"error": "Motivatsion matn topilmadi"}, status=404)

        serializer = MotivationSerializer(
            motivation,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "message": "Motivatsion matn yangilandi",
                "data": serializer.data
            }
        )

    # ✅ DELETE
    def delete(self, request, pk):
        try:
            motivation = Motivation.objects.get(pk=pk)
        except Motivation.DoesNotExist:
            return Response({"error": "Motivatsion matn topilmadi"}, status=404)

        motivation.delete()
        return Response(
            {"message": "Motivatsion matn o‘chirildi"},
            status=status.HTTP_204_NO_CONTENT
        )
