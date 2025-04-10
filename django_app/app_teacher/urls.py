from django.urls import path
from .views import(
     TeacherSubjectsAPIView, MyTopicAddCreateView,
       MyTopicListView, MyChapterAddCreateView, 
       MyChapterListView, QuestionAddCreateView
)
urlpatterns = [
    path("my-subjects/", TeacherSubjectsAPIView.as_view(), name="teacher-subjects"),
    path('my-chapters/create/', MyChapterAddCreateView.as_view(), name='chapter-create'),
    path('my-topics/create/', MyTopicAddCreateView.as_view(), name='topic-create'),
    path('my-question/create/', QuestionAddCreateView.as_view(), name='question-create'),

    path('my-chapters/list/<int:id>/', MyChapterListView.as_view(), name='my-chapters'),
    path('my-topics/list/<int:id>/', MyTopicListView.as_view(), name='my-topics'),
 

]