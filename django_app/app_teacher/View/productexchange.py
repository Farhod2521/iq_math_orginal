from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django_app.app_student.models import ProductExchange

from django_app.app_teacher.serializers import ProductExchangeSerializer
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404


class TeacherProductExchangeListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # ❗ Faqat Teacher kirishi mumkin
        teacher = getattr(request.user, "teacher_profile", None)
        if not teacher:
            return Response({"error": "Faqat o‘qituvchi kira oladi"}, status=403)

        queryset = ProductExchange.objects.all().order_by("-created_at")

        data = [
            {
                "id": obj.id,
                "student": obj.student.full_name,
                "product": obj.product.name,
                "used_coin": obj.used_coin,
                "delivery_status": obj.delivery_status,
                "created_at": obj.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for obj in queryset
        ]

        return Response({"results": data})


    def post(self, request):
        """📌 oldindan kelgan ID larni ko‘rildi deb belgilash"""
        teacher = getattr(request.user, "teacher_profile", None)
        if not teacher:
            return Response({"error": "Faqat o‘qituvchi kira oladi"}, status=403)

        ids = request.data.get("ids", [])

        if not isinstance(ids, list):
            return Response({"error": "ids ro‘yxat bo‘lishi kerak"}, status=400)

        updated = ProductExchange.objects.filter(
            id__in=ids,
            delivery_status="new"
        ).update(delivery_status="viewed")

        return Response({
            "message": f"{updated} ta buyurtma ko‘rildi deb belgilandi"
        })



class TeacherUpdateProductExchangeStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        # ❗ faqat Teacher
        teacher = getattr(request.user, "teacher_profile", None)
        if not teacher:
            return Response({"error": "Faqat o‘qituvchi kira oladi"}, status=403)

        exchange = get_object_or_404(ProductExchange, id=pk)

        new_status = request.data.get("delivery_status")

        allowed_status = ["preparing", "delivering", "delivered"]

        if new_status not in allowed_status:
            return Response(
                {"error": f"Status faqat {allowed_status} bo‘lishi mumkin"},
                status=400
            )

        exchange.delivery_status = new_status
        exchange.save()

        return Response({
            "message": "Status o‘zgartirildi",
            "id": exchange.id,
            "delivery_status": new_status
        })
