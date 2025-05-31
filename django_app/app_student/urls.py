from django.urls import path
from .views import (
     GenerateTestAPIView, CheckAnswersAPIView, 
     StudentSubjectListAPIView, ChapterListBySubjectAPIView,QuestionListByTopicAPIView,
     TopicListByChapterAPIView, GenerateCheckAnswersAPIView, StudentScoreAPIView, DiagnostLevelOverviewAPIView,
     DiagnostLevelDetailAPIView, Diagnostika_TopicDetailAPIView, PathFromIdsAPIView
)
from .View.product_exchange import ProductExchangeView, ProductExchangeListView

urlpatterns = [
    path('my-subjects/', StudentSubjectListAPIView.as_view(), name='my-subjects'),
    path('my-chapter/<int:subject_id>/', ChapterListBySubjectAPIView.as_view(), name='chapter-list-by-subject'),
    path('my-topic/<int:chapter_id>/', TopicListByChapterAPIView.as_view()),
    path('my-question/<int:topic_id>/', QuestionListByTopicAPIView.as_view()),
    path('my-generate-test/', GenerateTestAPIView.as_view(), name='generate-test'),
    path('my-generate-check-answer/', GenerateCheckAnswersAPIView.as_view(), name='my-check-answer'),
    path('my-check-answer/', CheckAnswersAPIView.as_view(), name='my-check-answer'),
    path('my-score/', StudentScoreAPIView.as_view(), name='student-score'),
    path('my-diagnost-level/', DiagnostLevelOverviewAPIView.as_view(), name='my-diagnost-level'),
    path('my-diagnost-detail/', DiagnostLevelDetailAPIView.as_view(), name='my-diagnost-level'),
    path('my-diagnost-topic-detail/<int:id>/', Diagnostika_TopicDetailAPIView.as_view(), name='my-diagnost-level'),

    path('my-products/exchange/<int:product_id>/', ProductExchangeView.as_view(), name='product-exchange'),
    path('my-products/exchange/list/', ProductExchangeListView.as_view(), name='product-list'),
    path('path/list/', PathFromIdsAPIView.as_view(), name='product-list'),


]
