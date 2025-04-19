from django.urls import path
from .views import (
     GenerateTestAPIView, CheckAnswersAPIView, 
     StudentSubjectListAPIView, ChapterListBySubjectAPIView
)

urlpatterns = [
    path('my-subjects/', StudentSubjectListAPIView.as_view(), name='my-subjects'),
    path('my-chapter/<int:id>/', ChapterListBySubjectAPIView.as_view(), name='chapter-list-by-subject'),
    path('my-generate-test/', GenerateTestAPIView.as_view(), name='generate-test'),
    path('my-check-answer/', CheckAnswersAPIView.as_view(), name='my-check-answer'),

]
