from django.urls import path
from .views import MySubjectsView, GenerateTestAPIView

urlpatterns = [
    path('my-subjects/', MySubjectsView.as_view(), name='my-subjects'),
    path('my-generate-test/', GenerateTestAPIView.as_view(), name='generate-test'),
]
