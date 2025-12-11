from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import BasePermission
from django_app.app_payments.models import SubscriptionPlan
from django_app.app_payments.serializers import SubscriptionPlanSerializer


class SubscriptionPlanCRUDAPIView(APIView):

    # 🔐 SUPERADMIN PERMISSION
    class IsSuperAdmin(BasePermission):
        def has_permission(self, request, view):
            return (
                request.user.is_authenticated
                and getattr(request.user, "role", None) == "superadmin"
            )

    permission_classes = [IsSuperAdmin]

    # 📌 GET — LIST yoki DETAIL
    def get(self, request, pk=None):
        if pk:
            try:
                plan = SubscriptionPlan.objects.get(pk=pk)
            except SubscriptionPlan.DoesNotExist:
                return Response({"error": "Tarif reja topilmadi"}, status=404)

            serializer = SubscriptionPlanSerializer(plan)
            return Response(serializer.data)

        plans = SubscriptionPlan.objects.all().order_by("-created_at")
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response(serializer.data)

    # 📌 CREATE
    def post(self, request):
        serializer = SubscriptionPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "Tarif reja yaratildi", "data": serializer.data},
            status=status.HTTP_201_CREATED
        )

    # 📌 UPDATE
    def put(self, request, pk):
        try:
            plan = SubscriptionPlan.objects.get(pk=pk)
        except SubscriptionPlan.DoesNotExist:
            return Response({"error": "Tarif reja topilmadi"}, status=404)

        serializer = SubscriptionPlanSerializer(plan, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "Tarif reja yangilandi", "data": serializer.data},
            status=200
        )

    # 📌 DELETE
    def delete(self, request, pk):
        try:
            plan = SubscriptionPlan.objects.get(pk=pk)
        except SubscriptionPlan.DoesNotExist:
            return Response({"error": "Tarif reja topilmadi"}, status=404)

        plan.delete()
        return Response({"message": "Tarif reja o‘chirildi"}, status=204)
