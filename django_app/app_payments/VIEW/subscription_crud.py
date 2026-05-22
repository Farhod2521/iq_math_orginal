from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import BasePermission, IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone

from django_app.app_payments.models import Subscription
from django_app.app_payments.serializers import (
    SubscriptionReadSerializer,
    SubscriptionCreateUpdateSerializer,
)


class IsSuperAdminOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and getattr(request.user, "role", None) in ("superadmin", "admin")
        )


# ════════════════════════════════════════════════════════
#  SUPERADMIN — barcha obunalar CRUD
#  GET    /api/payments/superadmin/subscriptions/
#  GET    /api/payments/superadmin/subscriptions/<pk>/
#  POST   /api/payments/superadmin/subscriptions/
#  PUT    /api/payments/superadmin/subscriptions/<pk>/
#  DELETE /api/payments/superadmin/subscriptions/<pk>/
# ════════════════════════════════════════════════════════
class SubscriptionCRUDAPIView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]

    # ── LIST / DETAIL ─────────────────────────────────
    def get(self, request, pk=None):
        if pk:
            sub = get_object_or_404(Subscription, pk=pk)
            return Response(SubscriptionReadSerializer(sub).data)

        qs = Subscription.objects.select_related(
            "student", "student__user"
        ).order_by("-start_date")

        # Filter: ?is_paid=true|false
        is_paid = request.query_params.get("is_paid")
        if is_paid is not None:
            qs = qs.filter(is_paid=is_paid.lower() == "true")

        # Filter: ?is_active=true|false
        is_active = request.query_params.get("is_active")
        if is_active is not None:
            now = timezone.now()
            if is_active.lower() == "true":
                qs = qs.filter(is_paid=True, end_date__gte=now)
            else:
                qs = qs.filter(is_paid=False) | qs.filter(end_date__lt=now)

        # Search: ?search=student_ismi
        search = request.query_params.get("search")
        if search:
            qs = qs.filter(student__full_name__icontains=search)

        serializer = SubscriptionReadSerializer(qs, many=True)
        return Response({"count": qs.count(), "results": serializer.data})

    # ── CREATE ────────────────────────────────────────
    def post(self, request, pk=None):
        serializer = SubscriptionCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sub = serializer.save()
        return Response(
            {
                "message": "Obuna yaratildi",
                "data": SubscriptionReadSerializer(sub).data,
            },
            status=status.HTTP_201_CREATED,
        )

    # ── UPDATE ────────────────────────────────────────
    def put(self, request, pk):
        sub = get_object_or_404(Subscription, pk=pk)
        serializer = SubscriptionCreateUpdateSerializer(
            sub, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        sub = serializer.save()
        return Response(
            {
                "message": "Obuna yangilandi",
                "data": SubscriptionReadSerializer(sub).data,
            }
        )

    # ── DELETE ────────────────────────────────────────
    def delete(self, request, pk):
        sub = get_object_or_404(Subscription, pk=pk)
        sub.delete()
        return Response(
            {"message": "Obuna o'chirildi"},
            status=status.HTTP_204_NO_CONTENT,
        )


# ════════════════════════════════════════════════════════
#  STUDENT — o'z obunasini ko'radi
#  GET /api/payments/my-subscription/
# ════════════════════════════════════════════════════════
class MySubscriptionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = getattr(request.user, "student_profile", None)
        if not student:
            return Response(
                {"error": "Siz student emassiz"},
                status=status.HTTP_403_FORBIDDEN,
            )
        sub = getattr(student, "subscription", None)
        if not sub:
            return Response(
                {"error": "Obuna topilmadi"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(SubscriptionReadSerializer(sub).data)
