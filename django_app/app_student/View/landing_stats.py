from django.core.cache import cache
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django_app.app_teacher.models import Topic
from django_app.app_user.models import Student

_CACHE_KEY = "landing-stats"
_CACHE_TTL = 600  # 10 daqiqa — landing har ochilganda bazaga so'rov ketmasin


class LandingStatsAPIView(APIView):
    """
    GET /api/v1/func_student/landing-stats/
    Landing sahifasi (iqmath.uz/math/uz) statistikasi — login talab qilinmaydi:
      students — ro'yxatdan o'tgan o'quvchilar soni;
      lessons  — faol fanlardagi darslar (mavzular) soni.
    """
    permission_classes = [AllowAny]
    # Eskirgan/noto'g'ri token bilan kelgan so'rov ham 401 olmasin
    authentication_classes = []

    def get(self, request):
        data = cache.get(_CACHE_KEY)
        if data is None:
            data = {
                "students": Student.objects.count(),
                "lessons": Topic.objects.filter(chapter__subject__active=True).count(),
            }
            cache.set(_CACHE_KEY, data, _CACHE_TTL)
        return Response(data)
