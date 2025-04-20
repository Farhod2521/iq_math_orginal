from django.urls import path
from .views import (
     GenerateTestAPIView, CheckAnswersAPIView, 
     StudentSubjectListAPIView, ChapterListBySubjectAPIView,QuestionListByTopicAPIView,
     TopicListByChapterAPIView, GenerateCheckAnswersAPIView, StudentScoreAPIView
)

urlpatterns = [
    path('my-subjects/', StudentSubjectListAPIView.as_view(), name='my-subjects'),
    path('my-chapter/<int:subject_id>/', ChapterListBySubjectAPIView.as_view(), name='chapter-list-by-subject'),
    path('my-topic/<int:chapter_id>/', TopicListByChapterAPIView.as_view()),
    path('my-question/<int:topic_id>/', QuestionListByTopicAPIView.as_view()),
    path('my-generate-test/', GenerateTestAPIView.as_view(), name='generate-test'),
    path('my-generate-check-answer/', GenerateCheckAnswersAPIView.as_view(), name='my-check-answer'),
    path('my-check-answer/', CheckAnswersAPIView.as_view(), name='my-check-answer'),
    path('my-score/', StudentScoreAPIView.as_view(), name='student-score'),

]
