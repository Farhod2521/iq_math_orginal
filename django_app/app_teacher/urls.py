from django.urls import path
from .views import(
     TeacherSubjectsAPIView, MyTopicAddCreateView,
       MyTopicListView, MyChapterAddCreateView, TextQuestionToXlsxImport,QuestionImportFromXlsx,
       MyChapterListView, QuestionAddCreateView, MyQuestionListView, QuestionUpdateView, QuestionDeleteView, SubjectListAPIView,
       ChoiceQuestionToXlsxImport, CompenQuestionToXlsxImport, UploadQuestionsAPIView, OpenAIQuestionListView, OpenAIProcessAPIView
)
from .View.unsolved import  TeacherUnsolvedQuestionReportListView, TeacherAnswerUnsolvedQuestionView
from  .View.gruop_student import AddStudentsToGroupAPIView, GroupCreateAPIView, GroupListAPIView, AddStudentsToGroupAPIView, StudentsWithoutGroupAPIView
from .View.reorderOrderIndex  import  ReorderTopicAPIView, ReorderChapterAPIView, ReorderSubjectAPIView
from .View.independentView import  TeacherTopicHelpRequestListAPIView, TeacherTopicHelpRequestDeleteAPIView,TeacherTopicHelpRequestDetailAPIView, GetTelegramIDFromHelpRequestAPIView,TeacherTopicHelpRequestFromTelegramAPIView,TeacherCommitToHelpRequestAPIView, TeacherHelpRequestNotificationAPIView
from .View.coupon import   CreateTeacherCouponAPIView
from .View.login_as_student import LoginAsStudentAPIView, ChangeStudentPasswordAPIView
from  .View.teacherreward import  TeacherRewardAPIView, TeacherRewardListAPIView
from  .View.productexchange import TeacherUpdateProductExchangeStatusAPIView, TeacherProductExchangeListAPIView
from .View.teacher_login_history import TeacherLoginHistoryListAPIView
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
    path("my-notifications/", TeacherHelpRequestNotificationAPIView.as_view(), name="teacher-notifications"),


    path('openai/questions/', OpenAIQuestionListView.as_view(), name='openai-question-list'),
    path('openai/process/', OpenAIProcessAPIView.as_view(), name='openai-process'),

    path("my-groups/create", GroupCreateAPIView.as_view(), name="group-list-create"),
    path("my-groups/list", GroupListAPIView.as_view(), name="group-list-create"),
    path("my-groups/detail/<int:pk>/", AddStudentsToGroupAPIView.as_view(), name="group-list-create"),
    path("my-groups/<int:group_id>/add-students/", AddStudentsToGroupAPIView.as_view(), name="group-add-students"),
    path('students/without-group/new-students/', StudentsWithoutGroupAPIView.as_view(), name='group-new-students'),


    path('topics/reorder/', ReorderTopicAPIView.as_view(), name='topic-reorder'),
    path('chapters/reorder/', ReorderChapterAPIView.as_view(), name='chapter-reorder'),
    path('subjects/reorder/', ReorderSubjectAPIView.as_view(), name='subject-reorder'),

    ############################################################################################ 
    path('teacher-independent/list/', TeacherTopicHelpRequestListAPIView.as_view(), name='subject-reorder'),
    path('teacher-independent/telegram-list/', TeacherTopicHelpRequestFromTelegramAPIView.as_view(), name='subject-reorder'),
    path('teacher-independent/detail/<int:id>/', TeacherTopicHelpRequestDetailAPIView.as_view(), name='subject-reorder'),
    path('teacher-independent/commit/', TeacherCommitToHelpRequestAPIView.as_view(), name='subject-reorder'),



    ####################################################################################################
    path('teacher/create-coupon/', CreateTeacherCouponAPIView.as_view(), name='teacher-create-coupon'),
        ####################################################################################################
    path('teacher/login-as-student/<int:student_id>/', LoginAsStudentAPIView.as_view(), name='login-as-student'),
    path('teacher/student/<int:student_id>/change-password/', ChangeStudentPasswordAPIView.as_view(), name='change-student-password'),


    ###########################################################################################################
    path('teacher/reward/', TeacherRewardAPIView.as_view(), name='teacher-reward'),
    path('teacher/reward/list/', TeacherRewardListAPIView.as_view(), name='teacher-reward-list'),
    path('teacher/help-request/<int:pk>/telegram-id/', GetTelegramIDFromHelpRequestAPIView.as_view(), name='get-telegram-id'),
    path('teacher/help-request/<int:pk>/delete/', TeacherTopicHelpRequestDeleteAPIView.as_view(), name='teacher-help-request-delete'),

    ######################################  PRODUCT EXCHANGE  LIST VIEW ######################################

    path('teacher/product-exchange-list/', TeacherProductExchangeListAPIView.as_view(), name='product-reward'),
    path('teacher/exchange/<int:pk>/status/', TeacherUpdateProductExchangeStatusAPIView.as_view(), name='product-reward'),
    #########################################  GENERETE QUESITON OPEN AI ############################################
    path('teacher/login-history-list/', TeacherLoginHistoryListAPIView.as_view(), name='product-reward'),




]