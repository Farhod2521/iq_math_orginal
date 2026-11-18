
from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from config.media import media_serve
from django_app.app_management.marketing_stats import market_stats_view
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf import settings
from django.conf.urls.static import static


schema_view = get_schema_view(
   openapi.Info(
      title="IQMATH",
      default_version='v1',
      description="API documentation for the student registration and login system",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="iqmathuzbekiston@gmail.com"),
      license=openapi.License(name="MIT License"),
   ),
   public=True,
   permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include("django_app.app_user.urls")),
    path('api/v1/func_teacher/', include("django_app.app_teacher.urls")),
    path('api/v1/func_student/', include("django_app.app_student.urls")),
    path('api/v1/management/', include("django_app.app_management.urls")),
    path('api/v1/payments/', include("django_app.app_payments.urls")),
    path('api/v1/tutor/', include("django_app.app_tutor.urls")),
    path('api/v1/func_chat/', include("django_app.app_chat.urls")),
    path('api/v1/universal/', include("django_app.app_unversial_view.urls")),
    path('api/v1/book/', include("django_app.app_book.urls")),
    path('api/v1/battle/', include("django_app.app_battle.urls")),
    path('api/v1/liga/', include("django_app.app_liga.urls")),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='swagger-docs'),
    # Marketing bo'limi statistikasi (4 xonali kod .env: MARKET_STATS_CODE).
    # Slashsiz variant ham kerak — aks holda pastdagi media catch-all uni ushlab 404 beradi.
    re_path(r'^market-statistika/?$', market_stats_view, name='market-statistika'),
]


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Yuklangan fayllar (rasm, video, hujjat). DEBUG ga bog'liq emas va faqat media fayllarni beradi —
# oldingi static(MEDIA_URL) loyiha papkasidagi hamma faylni (.env, kod) ochib qo'ygan edi.
urlpatterns += [re_path(r'^(?P<path>.+)$', media_serve)]