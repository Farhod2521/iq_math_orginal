from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .authentication import DEVICE_REVOKED_MESSAGE
from .device_service import DEVICE_CLAIM, is_device_active


class DeviceTokenRefreshSerializer(TokenRefreshSerializer):
    """O'chirilgan qurilmaning refresh tokeni bilan yangi access token berilmaydi."""

    def validate(self, attrs):
        refresh = RefreshToken(attrs["refresh"])
        device_id = refresh.get(DEVICE_CLAIM)
        if device_id and not is_device_active(device_id):
            raise InvalidToken(DEVICE_REVOKED_MESSAGE)
        return super().validate(attrs)


class DeviceTokenRefreshView(TokenRefreshView):
    serializer_class = DeviceTokenRefreshSerializer
