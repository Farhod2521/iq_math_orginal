from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import BasePermission

from django_app.app_management.models import Elon
from django_app.app_management.serializers import ElonSerializer

class ElonCRUDAPIView(APIView):

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
                elon = Elon.objects.get(pk=pk)
            except Elon.DoesNotExist:
                return Response({"error": "E'lon topilmadi"}, status=404)

            serializer = ElonSerializer(elon)
            return Response(serializer.data)

        # 📌 Agar pk bo‘lmasa — hammasini list qiladi
        elons = Elon.objects.all().order_by("-created_at")
        serializer = ElonSerializer(elons, many=True)
        return Response(serializer.data)

    # ✅ CREATE
    def post(self, request):
        serializer = ElonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "message": "E'lon yaratildi",
                "data": serializer.data
            },
            status=status.HTTP_201_CREATED
        )

    # ✅ UPDATE (TO‘LIQ yoki QISMAN)
    def put(self, request, pk):
        try:
            elon = Elon.objects.get(pk=pk)
        except Elon.DoesNotExist:
            return Response({"error": "E'lon topilmadi"}, status=404)

        serializer = ElonSerializer(elon, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "message": "E'lon yangilandi",
                "data": serializer.data
            }
        )

    # ✅ DELETE
    def delete(self, request, pk):
        try:
            elon = Elon.objects.get(pk=pk)
        except Elon.DoesNotExist:
            return Response({"error": "E'lon topilmadi"}, status=404)

        elon.delete()
        return Response({"message": "E'lon o‘chirildi"}, status=204)
