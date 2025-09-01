from django.urls import path
from .views import (
      UniversalVerifySmsCodeAPIView, LoginAPIView, 
     StudentProfileAPIView, StudentsListView, ForgotPasswordView, VerifySMSCodeView,
    ResetPasswordView, ResendSMSCodeView,
    LogoutDeviceAPIView, RegisterAPIView, RegisterTeacherAPIView, TeacherVerifySmsCodeAPIView,
    ClassListView, TeacherLoginAPIView, TeacherProfileAPIView, UpdateStudentFieldAPIView, UserProfileAPIView,
      LogoutAPIView, TelegramIDCheckAPIView, ParentCreateAPIView, UpdateTelegramIDAPIView, AddChildRequestAPIView,
      ConfirmChildAPIView, ParentChildrenListAPIView

)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
urlpatterns = [
    ###################################################################################
    #########################  STUDENT  ################################################
    ###################################################################################
    path('student/register/', RegisterAPIView.as_view(), name='register_student'),
    path('student/register-verify-sms/', UniversalVerifySmsCodeAPIView.as_view(), name='verify_sms'),#register
    path('student/login/', LoginAPIView.as_view(), name='login'),
    path('student/logout/', LogoutAPIView.as_view(), name='login'),
    path('student/profile/', StudentProfileAPIView.as_view(), name='profile'),
    path('student/profile-update/', UpdateStudentFieldAPIView.as_view(), name='profile'),
    path('student/student_list/', StudentsListView.as_view(), name='student_list'),
    path('student/forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('student/verify-sms-code/', VerifySMSCodeView.as_view(), name='verify-sms-code'),###foget-pasword
    path('student/reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('student/resend-sms-code/', ResendSMSCodeView.as_view(), name='resend-sms-code'), 
    path('student/logout_device/', LogoutDeviceAPIView.as_view(), name='logout_device'), 


    ###################################################################################
    #########################  TEACHER ################################################
    ###################################################################################
    path('teacher/register/', RegisterTeacherAPIView.as_view(), name='register_teacher'),
    path('teacher/register-verify-sms/', TeacherVerifySmsCodeAPIView.as_view(), name='verify_sms'),
    path('teacher/login/', TeacherLoginAPIView.as_view(), name='login'),
    path('teacher/profile/', TeacherProfileAPIView.as_view(), name='profile'),
    ###################################################################################
    #########################  TEACHER ################################################
    ###################################################################################
    path('user/profile/', UserProfileAPIView.as_view(), name='register_teacher'),


    ###################################################################################
    #########################  CLASS   ################################################
    ###################################################################################
    path('class/class_name_listview/', ClassListView.as_view(), name='class_name_listview'),

    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('check-telegram-id/', TelegramIDCheckAPIView.as_view(), name='token_refresh'),

    path('update-telegram-id/', UpdateTelegramIDAPIView.as_view(), name='update-telegram-id'),
    #####################################################################################
    path("parent/add-child/", AddChildRequestAPIView.as_view()),
    path("parent/confirm-child/", ConfirmChildAPIView.as_view()),
    path("parent/confirm-child/list/", ParentChildrenListAPIView.as_view()),

]




