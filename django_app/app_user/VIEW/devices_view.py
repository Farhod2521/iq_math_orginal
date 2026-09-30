from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_app.app_user.device_service import (
    DEVICE_CLAIM,
    MAX_ACTIVE_DEVICES,
    deactivate_device,
    serialize_device,
)
from django_app.app_user.models import UserDevice


def _current_device_id(request):
    token = getattr(request, "auth", None)
    try:
        return token.get(DEVICE_CLAIM) if token is not None else None
    except AttributeError:
        return None


class MyDevicesAPIView(APIView):
    """
    GET /api/v1/auth/user/devices/?status=active|all
    Foydalanuvchining qurilmalari: faol qurilmalar (standart) yoki chiqarilganlari bilan birga.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        current_id = _current_device_id(request)
        devices = UserDevice.objects.filter(user=request.user)
        if request.query_params.get("status") != "all":
            devices = devices.filter(is_active=True)
        devices = sorted(
            devices[:50],
            # Joriy qurilma birinchi, keyin faollar, keyin oxirgi faollik bo'yicha
            key=lambda d: (str(d.id) != str(current_id), not d.is_active, -(d.last_used_at.timestamp() if d.last_used_at else 0)),
        )
        return Response({
            "max_devices": MAX_ACTIVE_DEVICES,
            "active_count": UserDevice.objects.filter(user=request.user, is_active=True).count(),
            "current_device_id": current_id,
            "devices": [serialize_device(device, current_id) for device in devices],
        })


class MyDeviceDetailAPIView(APIView):
    """
    DELETE /api/v1/auth/user/devices/<uuid>/
    Qurilmani hisobdan chiqarib yuborish. O'sha qurilmadagi keyingi so'rov 401 bilan qaytadi.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, device_id):
        device = get_object_or_404(UserDevice, id=device_id, user=request.user)
        deactivate_device(device)
        return Response(
            {
                "detail": "Qurilma hisobingizdan chiqarildi.",
                "was_current": str(device.id) == str(_current_device_id(request)),
            },
            status=status.HTTP_200_OK,
        )
