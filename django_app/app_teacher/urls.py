from django.urls import path
from .views import(
     TeacherSubjectsAPIView, MyTopicAddCreateView,
       MyTopicListView, MyChapterAddCreateView, TextQuestionToXlsxImport,QuestionImportFromXlsx,
       MyChapterListView, QuestionAddCreateView, MyQuestionListView, QuestionUpdateView, QuestionDeleteView, SubjectListAPIView,
       ChoiceQuestionToXlsxImport, CompenQuestionToXlsxImport, UploadQuestionsAPIView, OpenAIQuestionListView, OpenAIProcessAPIView
)
from .View.unsolved import  TeacherUnsolvedQuestionReportListView, TeacherAnswerUnsolvedQuestionView
from  .View.gruop_student import AddStudentsToGroupAPIView, GroupCreateAPIView, GroupListAPIView, GroupDetailAPIView
urlpatterns = [
    path("my-subjects/", TeacherSubjectsAPIView.as_view(), name="teacher-subjects"),
    path("subject-list/", SubjectListAPIView.as_view(), name="teacher-subjects"),
    path("my-subjects/<int:pk>/", TeacherSubjectsAPIView.as_view(), name="teacher-subjects"),
    path('my-chapters/create/', MyChapterAddCreateView.as_view(), name='chapter-create'),
    path('my-topics/create/', MyTopicAddCreateView.as_view(), name='topic-create'),
    path('my-question/create/', QuestionAddCreateView.as_view(), name='question-create'),
    path('my-question/update/<int:pk>/', QuestionUpdateView.as_view(), name='question-update'),
    path('my-question/delete/<int:pk>/', QuestionDeleteView.as_view(), name='question-delete'),
    path('my-question/list/<int:id>/', MyQuestionListView.as_view(), name='question-list'),

    path('my-chapters/list/<int:id>/', MyChapterListView.as_view(), name='my-chapters'),
    path('my-topics/list/<int:id>/', MyTopicListView.as_view(), name='my-topics'),
    path('text-export/', TextQuestionToXlsxImport.as_view(), name='my-topics'),
    path('choice-export/', ChoiceQuestionToXlsxImport.as_view(), name='my-topics'),
    path('composite-export/', CompenQuestionToXlsxImport.as_view(), name='my-topics'),
    path('xlsx-import/', QuestionImportFromXlsx.as_view(), name='my-topics'),
    path('word-import/', UploadQuestionsAPIView.as_view(), name='my-topics'),
    path('my-unsolved-question/list/', TeacherUnsolvedQuestionReportListView.as_view(), name='unsolved-question-list'),
    path('my-unsolved-question/answer/', TeacherAnswerUnsolvedQuestionView.as_view(), name='unsolved-question-answer'),


    path('openai/questions/', OpenAIQuestionListView.as_view(), name='openai-question-list'),
    path('openai/process/', OpenAIProcessAPIView.as_view(), name='openai-process'),

    path("my-groups/create", GroupCreateAPIView.as_view(), name="group-list-create"),
    path("my-groups/list", GroupListAPIView.as_view(), name="group-list-create"),
    path("my-groups/detail", GroupDetailAPIView.as_view(), name="group-list-create"),
    path("my-groups/<int:group_id>/add-students/", AddStudentsToGroupAPIView.as_view(), name="group-add-students"),

]