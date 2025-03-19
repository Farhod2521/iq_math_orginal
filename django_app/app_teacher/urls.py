from django.urls import path
from .views import TeacherSubjectsAPIView

urlpatterns = [
    path("my-subjects/", TeacherSubjectsAPIView.as_view(), name="teacher-subjects"),
]