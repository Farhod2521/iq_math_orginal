
from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
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
      contact=openapi.Contact(email="your-email@example.com"),
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
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='swagger-docs'),
]


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)