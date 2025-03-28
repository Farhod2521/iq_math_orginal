from django.urls import path
from .views import(
     TeacherSubjectsAPIView, MyTopicAddCreateView,
       MyTopicListView, MyChapterAddCreateView, 
       MyChapterListView, QuestionAddCreateView, MyQuestionListView
)
urlpatterns = [
    path("my-subjects/", TeacherSubjectsAPIView.as_view(), name="teacher-subjects"),
    path('my-chapters/create/', MyChapterAddCreateView.as_view(), name='chapter-create'),
    path('my-topics/create/', MyTopicAddCreateView.as_view(), name='topic-create'),
    path('my-questions/create/', QuestionAddCreateView.as_view(), name='question-create'),
    path('my-chapters/list/', MyChapterListView.as_view(), name='my-chapters'),
    path('my-topics/list/<int:id>/', MyTopicListView.as_view(), name='my-topics'),
    path('my-questions/<int:id>/', MyQuestionListView.as_view(), name='my-questions'),

]