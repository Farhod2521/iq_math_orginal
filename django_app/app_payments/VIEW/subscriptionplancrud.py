from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import BasePermission
from django_app.app_payments.models import SubscriptionPlan, SubscriptionBenefit, SubscriptionCategory
from django_app.app_payments.serializers import SubscriptionPlanCREATESerializer, SubscriptionREADPlanSerializer

from django.shortcuts import get_object_or_404
from .subscriptionplan_serizlizers import  (
    SubscriptionBenefitCreateSerializer, SubscriptionBenefitReadSerializer,
    SubscriptionCategoryCreateSerializer, SubscriptionCategoryReadSerializer
)
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


#===============================
#🔹 SUBSCRIPTION CATEGORY CRUD
#===============================
class SubscriptionCategoryCRUDAPIView(APIView):

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
            category = get_object_or_404(SubscriptionCategory, pk=pk)
            serializer = SubscriptionCategoryReadSerializer(category)
            return Response(serializer.data)

        categories = SubscriptionCategory.objects.all().order_by("-created_at")
        serializer = SubscriptionCategoryReadSerializer(categories, many=True)
        return Response(serializer.data)

    # 📌 CREATE
    def post(self, request):
        serializer = SubscriptionCategoryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()

        return Response(
            {
                "message": "Kategoriya yaratildi",
                "data": SubscriptionCategoryReadSerializer(category).data
            },
            status=status.HTTP_201_CREATED
        )

    # 📌 UPDATE
    def put(self, request, pk):
        category = get_object_or_404(SubscriptionCategory, pk=pk)
        serializer = SubscriptionCategoryCreateSerializer(
            category, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        category = serializer.save()

        return Response(
            {
                "message": "Kategoriya yangilandi",
                "data": SubscriptionCategoryReadSerializer(category).data
            }
        )

    # 📌 DELETE
    def delete(self, request, pk):
        category = get_object_or_404(SubscriptionCategory, pk=pk)
        category.delete()
        return Response(
            {"message": "Kategoriya o‘chirildi"},
            status=status.HTTP_204_NO_CONTENT
        )

#===============================
#🔹 SUBSCRIPTION BENEFIT CRUD
#===============================
class SubscriptionBenefitCRUDAPIView(APIView):

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
            benefit = get_object_or_404(SubscriptionBenefit, pk=pk)
            serializer = SubscriptionBenefitReadSerializer(benefit)
            return Response(serializer.data)

        benefits = SubscriptionBenefit.objects.all().order_by("-created_at")
        serializer = SubscriptionBenefitReadSerializer(benefits, many=True)
        return Response(serializer.data)

    # 📌 CREATE
    def post(self, request):
        serializer = SubscriptionBenefitCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        benefit = serializer.save()

        return Response(
            {
                "message": "Ustunlik yaratildi",
                "data": SubscriptionBenefitReadSerializer(benefit).data
            },
            status=status.HTTP_201_CREATED
        )

    # 📌 UPDATE
    def put(self, request, pk):
        benefit = get_object_or_404(SubscriptionBenefit, pk=pk)
        serializer = SubscriptionBenefitCreateSerializer(
            benefit, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        benefit = serializer.save()

        return Response(
            {
                "message": "Ustunlik yangilandi",
                "data": SubscriptionBenefitReadSerializer(benefit).data
            }
        )

    # 📌 DELETE
    def delete(self, request, pk):
        benefit = get_object_or_404(SubscriptionBenefit, pk=pk)
        benefit.delete()
        return Response(
            {"message": "Ustunlik o‘chirildi"},
            status=status.HTTP_204_NO_CONTENT
        )

