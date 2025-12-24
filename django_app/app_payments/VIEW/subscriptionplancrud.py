from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import BasePermission
from django_app.app_payments.models import SubscriptionPlan
from django_app.app_payments.serializers import SubscriptionPlanCREATESerializer, SubscriptionREADPlanSerializer

from django.shortcuts import get_object_or_404
class SubscriptionPlanCRUDAPIView(APIView):

    # 🔐 SUPERADMIN
    class IsSuperAdmin(BasePermission):
        def has_permission(self, request, view):
            return (
                request.user.is_authenticated
                and getattr(request.user, "role", None) == "superadmin"
            )

    permission_classes = [IsSuperAdmin]

    # 📌 GET — LIST / DETAIL
    def get(self, request, pk=None):
        if pk:
            plan = get_object_or_404(SubscriptionPlan, pk=pk)
            serializer = SubscriptionREADPlanSerializer(plan)
            return Response(serializer.data)

        plans = SubscriptionPlan.objects.all().order_by("-created_at")
        serializer = SubscriptionREADPlanSerializer(plans, many=True)
        return Response(serializer.data)

    # 📌 CREATE
    def post(self, request):
        serializer = SubscriptionPlanCREATESerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.save()

        return Response(
            {
                "message": "Tarif reja yaratildi",
                "data": SubscriptionREADPlanSerializer(plan).data
            },
            status=status.HTTP_201_CREATED
        )

    # 📌 UPDATE
    def put(self, request, pk):
        plan = get_object_or_404(SubscriptionPlan, pk=pk)

        serializer = SubscriptionPlanCREATESerializer(
            plan, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        plan = serializer.save()

        return Response(
            {
                "message": "Tarif reja yangilandi",
                "data": SubscriptionREADPlanSerializer(plan).data
            }
        )

    # 📌 DELETE
    def delete(self, request, pk):
        plan = get_object_or_404(SubscriptionPlan, pk=pk)
        plan.delete()
        return Response(
            {"message": "Tarif reja o‘chirildi"},
            status=status.HTTP_204_NO_CONTENT
        )
