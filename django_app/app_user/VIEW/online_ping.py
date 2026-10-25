"""
POST /api/v1/auth/online/ping/ — sayt ochiq (va ko'rinib) turganda daqiqada bir yuboriladi.
Sessiyani token tekshiruvining o'zi yangilaydi (DeviceJWTAuthentication → touch_online),
shu sababli bu yerda faqat bo'sh javob qaytariladi.
"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class OnlinePingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response(status=204)
