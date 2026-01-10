from django.urls import path
from .views import (
     GenerateTestAPIView, CheckAnswersAPIView, 
     StudentSubjectListAPIView, ChapterListBySubjectAPIView,QuestionListByTopicAPIView,
     TopicListByChapterAPIView, GenerateCheckAnswersAPIView, StudentScoreAPIView, DiagnostLevelOverviewAPIView,
     DiagnostLevelDetailAPIView, Diagnostika_TopicDetailAPIView, PathFromIdsAPIView, PathFromIdsStudentAPIView,
     ChapterListBySubject_STUDENT_ID_APIView, TopicListByChapter_STUDENT_ID_APIView
)
from .View.app_diagnost import StudentDiagnostSubjectsAPIView, SubjectChaptersAPIView, ChapterTopicsAPIView, StudentDiagnosticHistoryAPIView, ParentStudentDiagnosticHistoryAPIView
from .View.product_exchange import ProductExchangeView, ProductExchangeListView, ProductExchangeConfirmAPIView
from  .View.unsolvedquestioncreateView import UnsolvedQuestionCreateView, UnsolvedQuestionReportListView
from .View.student_statistics import StudentStatisticsDetailAPIView, SubjectListWithMasteryAPIView, ChapterTopicProgressAPIView, DiagnostSubjectListAPIView, MyReferralsAPIView ,DiagnostChapterTopicProgressAPIView
from .View.independentView import  TopicHelpRequestCreateView, AssignTeacherAPIView, GetTelegramIdFromTopicHelpAPIView, StudentTopicHelpRequestListView, TopicHelpRequestIndependentDetailAPIView
from .View.student_login_history import  StudentLoginHistoryListAPIView
from .View.convertView import ConvertView
from .View.coupon_create_apiview import StudentCouponAPIView
from .View.student_next_topic_mobile_app import  StudentNextTopicAPIView, StudentLastProgressAPIView
from .View.mobile_app import StudentRatingAPIView, WeeklyStudyStatsAPIView, StudentTopAPIView, SubjectProgressAPIView, SubjectCategoryDetailAPIView
from .View.daily_Math_Pop_Up import  SubmitQuickMathAnswerAPIView, QuickMathQuestionAPIView

urlpatterns = [
    path('my-subjects/', StudentSubjectListAPIView.as_view(), name='my-subjects'),
    path('my-chapter/<int:subject_id>/', ChapterListBySubjectAPIView.as_view(), name='chapter-list-by-subject'),
    path('my-chapter/student_id/<int:subject_id>/', ChapterListBySubject_STUDENT_ID_APIView.as_view(), name='chapter-list-by-subject'),
    path('my-topic/student_id/<int:chapter_id>/', TopicListByChapter_STUDENT_ID_APIView.as_view(), name='chapter-list-by-subject'),
    path('my-topic/<int:chapter_id>/', TopicListByChapterAPIView.as_view()),
    path('my-question/<int:topic_id>/', QuestionListByTopicAPIView.as_view()),
    path('my-generate-test/', GenerateTestAPIView.as_view(), name='generate-test'),
    path('my-generate-check-answer/', GenerateCheckAnswersAPIView.as_view(), name='my-check-answer'),
    path('my-check-answer/', CheckAnswersAPIView.as_view(), name='my-check-answer'),
    path('my-score/', StudentScoreAPIView.as_view(), name='student-score'),
    path('my-diagnost-level/', DiagnostLevelOverviewAPIView.as_view(), name='my-diagnost-level'),
    path('my-diagnost-detail/', DiagnostLevelDetailAPIView.as_view(), name='my-diagnost-level'),
    path('my-diagnost-topic-detail/<int:id>/', Diagnostika_TopicDetailAPIView.as_view(), name='my-diagnost-level'),
    path('my-diagnost/history/progress/', StudentDiagnosticHistoryAPIView.as_view(), name='student-diagnostic-progress'),
    path("parent/student-diagnostic-history/", ParentStudentDiagnosticHistoryAPIView.as_view(), name='student-diagnostic-progress'),


    path('my-products/exchange/<int:product_id>/', ProductExchangeView.as_view(), name='product-exchange'),
    path('my-products/exchange/list/', ProductExchangeListView.as_view(), name='product-list'),
    path('my-product-exchange/<int:pk>/confirm/', ProductExchangeConfirmAPIView.as_view(), name='product-list'),
    path('my-unsolved-question/create/', UnsolvedQuestionCreateView.as_view(), name='unsolved-question-create'),
    path('my-unsolved-question/list/', UnsolvedQuestionReportListView.as_view(), name='unsolved-question-list'),
    path('path/list/', PathFromIdsAPIView.as_view(), name='product-list'),
    path('path/list/student_id/', PathFromIdsStudentAPIView.as_view(), name='product-list'),



##################################  DIAGNISTIKA #####################################################
    path('my-diagnost-subjects/', StudentDiagnostSubjectsAPIView.as_view()),
    path('my-diagnost-subject/<int:subject_id>/chapters/', SubjectChaptersAPIView.as_view()),
    path('my-diagnost-chapter/<int:chapter_id>/topics/', ChapterTopicsAPIView.as_view()),
    

##########################################################################################
    path('student-statistics/<int:student_id>/', StudentStatisticsDetailAPIView.as_view()),
    path('students/<int:student_id>/subjects/', SubjectListWithMasteryAPIView.as_view(), name='subject-list-with-mastery'),
    path('students/<int:student_id>/subjects/<int:subject_id>/chapters/', ChapterTopicProgressAPIView.as_view(), name='chapter-topic-progress'),
    path('diagnost/students/<int:student_id>/subjects/', DiagnostSubjectListAPIView.as_view(), name='subject-list-with-mastery'),
    path('diagnost/students/<int:student_id>/subjects/<int:subject_id>/chapters/', DiagnostChapterTopicProgressAPIView.as_view(), name='chapter-topic-progress'),
    path('my-referrals/', MyReferralsAPIView.as_view(), name='my-referrals'),


###################################################################################################################################
    path('student-independent/', TopicHelpRequestCreateView.as_view()),
    path("student/telegram/assign-teacher/", AssignTeacherAPIView.as_view(), name="assign_teacher"),
    path("student/student_id/telegram_id/", GetTelegramIdFromTopicHelpAPIView.as_view(), name="assign_teacher"),
    path("my-independent/", StudentTopicHelpRequestListView.as_view(), name="independent"),
    path("id-independent/<int:pk>/", TopicHelpRequestIndependentDetailAPIView.as_view(), name="independent"),



    path('student/login-history/', StudentLoginHistoryListAPIView.as_view(), name='student-login-history'),
    path('my-convert/', ConvertView.as_view(), name='convert'),
    path("student/coupon/", StudentCouponAPIView.as_view(), name='convert'),


    ###############################################  MOBILE APP ##################################################
    path("student/next-topic/app", StudentNextTopicAPIView.as_view(), name='convert'),
    path("student/last-topic-result/app", StudentLastProgressAPIView.as_view(), name='convert'),
    path("student/rating/app", StudentRatingAPIView.as_view(), name='convert'),
    path("student/weklystudystats/app", WeeklyStudyStatsAPIView.as_view(), name='convert'),
    path("student/studenttop/app", StudentTopAPIView.as_view(), name='convert'),
    path("student/subjectprogress/app", SubjectProgressAPIView.as_view(), name='convert'),
    path("student/subject-category-detail/app", SubjectCategoryDetailAPIView.as_view(), name='convert'),
    path("quick-math/question/", QuickMathQuestionAPIView.as_view()),
    path("quick-math/submit/", SubmitQuickMathAnswerAPIView.as_view()),
]
