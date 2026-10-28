from django.core.cache import cache
from django.db.models import Q
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django_app.app_payments.models import SubscriptionSetting
from django_app.app_teacher.models import Topic
from django_app.app_user.models import Student, User

_CACHE_KEY = "landing-stats:v4"
_CACHE_TTL = 600  # 10 daqiqa — landing har ochilganda bazaga so'rov ketmasin

# Saytdagi "ro'yxatdan o'tganlar" soniga kiradigan rollar (faol va nofaol — hammasi)
_USER_ROLES = ("student", "parent", "tutor", "teacher")


def _has(field):
    return Q(**{f"{field}__isnull": False}) & ~Q(**{field: ""})


class LandingStatsAPIView(APIView):
    """
    GET /api/v1/func_student/landing-stats/
    Landing, bosh sahifa va "Biz haqimizda" statistikasi — login talab qilinmaydi:
      users      — ro'yxatdan o'tgan barcha foydalanuvchilar (o'quvchi, ota-ona, o'qituvchi, mentor; faol va nofaol);
      students   — shulardan o'quvchilar soni;
      lessons    — faol fanlardagi darslar (mavzular) soni;
      videos     — video darslar soni: o'zbekcha va ruscha videolar alohida sanaladi;
      trial_days — ro'yxatdan o'tganda beriladigan bepul muddat (kun).
    """
    permission_classes = [AllowAny]
    # Eskirgan/noto'g'ri token bilan kelgan so'rov ham 401 olmasin
    authentication_classes = []

    def get(self, request):
        data = cache.get(_CACHE_KEY)
        if data is None:
            topics = Topic.objects.filter(chapter__subject__active=True)
            data = {
                "users": User.objects.filter(role__in=_USER_ROLES).count(),
                "students": Student.objects.count(),
                "lessons": topics.count(),
                "videos": topics.filter(_has("video_url_uz")).count() + topics.filter(_has("video_url_ru")).count(),
                # Ro'yxatdan o'tishdagi bilan bir xil manba (sozlama bo'lmasa — 7 kun)
                "trial_days": getattr(SubscriptionSetting.objects.first(), "free_trial_days", 7),
            }
            cache.set(_CACHE_KEY, data, _CACHE_TTL)
        return Response(data)
