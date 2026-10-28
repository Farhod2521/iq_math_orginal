from django.core.cache import cache
from django.db.models import Q
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django_app.app_teacher.models import Topic
from django_app.app_user.models import Student

_CACHE_KEY = "landing-stats:v2"
_CACHE_TTL = 600  # 10 daqiqa — landing har ochilganda bazaga so'rov ketmasin


class LandingStatsAPIView(APIView):
    """
    GET /api/v1/func_student/landing-stats/
    Landing sahifasi (iqmath.uz/math/uz) statistikasi — login talab qilinmaydi:
      students — ro'yxatdan o'tgan o'quvchilar soni;
      lessons  — faol fanlardagi darslar (mavzular) soni;
      videos   — shulardan videosi (uz yoki ru) bor darslar soni.
    """
    permission_classes = [AllowAny]
    # Eskirgan/noto'g'ri token bilan kelgan so'rov ham 401 olmasin
    authentication_classes = []

    def get(self, request):
        data = cache.get(_CACHE_KEY)
        if data is None:
            topics = Topic.objects.filter(chapter__subject__active=True)
            has_video = (Q(video_url_uz__isnull=False) & ~Q(video_url_uz="")) | (
                Q(video_url_ru__isnull=False) & ~Q(video_url_ru="")
            )
            data = {
                "students": Student.objects.count(),
                "lessons": topics.count(),
                "videos": topics.filter(has_video).count(),
            }
            cache.set(_CACHE_KEY, data, _CACHE_TTL)
        return Response(data)
