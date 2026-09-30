# DIQQAT: bu modul DEFAULT_AUTHENTICATION_CLASSES orqali rest_framework.views yuklanayotgan paytda
# import qilinadi. Shu sababli bu yerda rest_framework.views / generics ga olib boruvchi importlar
# (simplejwt.views, simplejwt.serializers) bo'lmasligi kerak — aks holda aylanma import xatosi chiqadi.
# Token yangilash view'i token_refresh.py da.
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed

DEVICE_REVOKED_MESSAGE = "Bu qurilma hisobingizdan chiqarib yuborilgan. Qaytadan kiring."


class DeviceJWTAuthentication(JWTAuthentication):
    """
    Oddiy JWT tekshiruvi + qurilma tekshiruvi: tokenda qurilma (did) bo'lsa va u
    "Qurilmalar" bo'limidan o'chirilgan bo'lsa — so'rov 401 bilan rad etiladi.
    Qurilmasiz tokenlar (boshqa rollar, eski tokenlar) avvalgidek ishlaydi.
    """

    def get_validated_token(self, raw_token):
        from .device_service import DEVICE_CLAIM, is_device_active

        token = super().get_validated_token(raw_token)
        device_id = token.get(DEVICE_CLAIM)
        if device_id and not is_device_active(device_id):
            raise AuthenticationFailed(DEVICE_REVOKED_MESSAGE, code="device_revoked")
        return token
