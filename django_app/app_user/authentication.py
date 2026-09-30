from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .device_service import DEVICE_CLAIM, is_device_active

DEVICE_REVOKED_MESSAGE = "Bu qurilma hisobingizdan chiqarib yuborilgan. Qaytadan kiring."


class DeviceJWTAuthentication(JWTAuthentication):
    """
    Oddiy JWT tekshiruvi + qurilma tekshiruvi: tokenda qurilma (did) bo'lsa va u
    "Qurilmalar" bo'limidan o'chirilgan bo'lsa — so'rov 401 bilan rad etiladi.
    Qurilmasiz tokenlar (boshqa rollar, eski tokenlar) avvalgidek ishlaydi.
    """

    def get_validated_token(self, raw_token):
        token = super().get_validated_token(raw_token)
        device_id = token.get(DEVICE_CLAIM)
        if device_id and not is_device_active(device_id):
            raise AuthenticationFailed(DEVICE_REVOKED_MESSAGE, code="device_revoked")
        return token


class DeviceTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        refresh = RefreshToken(attrs["refresh"])
        device_id = refresh.get(DEVICE_CLAIM)
        if device_id and not is_device_active(device_id):
            raise InvalidToken(DEVICE_REVOKED_MESSAGE)
        return super().validate(attrs)


class DeviceTokenRefreshView(TokenRefreshView):
    serializer_class = DeviceTokenRefreshSerializer
