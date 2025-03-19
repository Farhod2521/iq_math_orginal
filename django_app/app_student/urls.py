from django.urls import path
from .views import MySubjectsView

urlpatterns = [
    path('my-subjects/', MySubjectsView.as_view(), name='my-subjects'),
]
