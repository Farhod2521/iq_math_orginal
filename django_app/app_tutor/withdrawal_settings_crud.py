from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import BasePermission
from django.shortcuts import get_object_or_404

from .models import WithdrawalLimitSettings


class IsSuperAdminOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and getattr(request.user, "role", None) in ("superadmin", "admin")
        )


def _serialize(obj):
    return {
        "id": obj.id,
        "min_amount": float(obj.min_amount),
        "max_amount": float(obj.max_amount),
        "updated_at": obj.updated_at.strftime("%d/%m/%Y %H:%M"),
    }


def _validate_amounts(min_amount, max_amount):
    try:
        mn = float(min_amount)
        mx = float(max_amount)
    except (TypeError, ValueError):
        return None, None, "min_amount va max_amount raqam bo'lishi kerak"
    if mn >= mx:
        return None, None, "min_amount max_amount dan kichik bo'lishi kerak"
    return mn, mx, None


# ════════════════════════════════════════════════════════
#  GET    /api/v1/superadmin/withdrawal-settings/
#  GET    /api/v1/superadmin/withdrawal-settings/<pk>/
#  POST   /api/v1/superadmin/withdrawal-settings/
#  PUT    /api/v1/superadmin/withdrawal-settings/<pk>/
#  PATCH  /api/v1/superadmin/withdrawal-settings/<pk>/
#  DELETE /api/v1/superadmin/withdrawal-settings/<pk>/
# ════════════════════════════════════════════════════════
class WithdrawalLimitSettingsCRUDAPIView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]

    # ── LIST / DETAIL ─────────────────────────────────
    def get(self, request, pk=None):
        if pk:
            obj = get_object_or_404(WithdrawalLimitSettings, pk=pk)
            return Response(_serialize(obj))

        qs = WithdrawalLimitSettings.objects.order_by("id")
        results = [_serialize(o) for o in qs]
        return Response({"count": len(results), "results": results})

    # ── CREATE ────────────────────────────────────────
    def post(self, request, pk=None):
        min_amount = request.data.get("min_amount")
        max_amount = request.data.get("max_amount")

        if min_amount is None or max_amount is None:
            return Response(
                {"error": "min_amount va max_amount majburiy"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        mn, mx, err = _validate_amounts(min_amount, max_amount)
        if err:
            return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)

        obj = WithdrawalLimitSettings.objects.create(min_amount=mn, max_amount=mx)
        return Response(_serialize(obj), status=status.HTTP_201_CREATED)

    # ── FULL UPDATE ───────────────────────────────────
    def put(self, request, pk):
        obj = get_object_or_404(WithdrawalLimitSettings, pk=pk)

        min_amount = request.data.get("min_amount")
        max_amount = request.data.get("max_amount")

        if min_amount is None or max_amount is None:
            return Response(
                {"error": "min_amount va max_amount majburiy"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        mn, mx, err = _validate_amounts(min_amount, max_amount)
        if err:
            return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)

        obj.min_amount = mn
        obj.max_amount = mx
        obj.save()
        return Response(_serialize(obj))

    # ── PARTIAL UPDATE ────────────────────────────────
    def patch(self, request, pk):
        obj = get_object_or_404(WithdrawalLimitSettings, pk=pk)

        min_amount = request.data.get("min_amount", obj.min_amount)
        max_amount = request.data.get("max_amount", obj.max_amount)

        mn, mx, err = _validate_amounts(min_amount, max_amount)
        if err:
            return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)

        obj.min_amount = mn
        obj.max_amount = mx
        obj.save()
        return Response(_serialize(obj))

    # ── DELETE ────────────────────────────────────────
    def delete(self, request, pk):
        obj = WithdrawalLimitSettings.objects.filter(pk=pk).first()
        if not obj:
            return Response(
                {"error": "Sozlama topilmadi"},
                status=status.HTTP_404_NOT_FOUND,
            )
        obj.delete()
        return Response({"success": "Sozlama o'chirildi"})
