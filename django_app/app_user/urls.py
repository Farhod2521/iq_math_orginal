from django.urls import path
from .views import (
      StudentVerifySmsCodeAPIView, LoginAPIView, 
     StudentProfileAPIView, StudentsListView, ForgotPasswordView, VerifySMSCodeView,
    ResetPasswordView, ResendSMSCodeView,
    LogoutDeviceAPIView, RegisterStudentAPIView, RegisterTeacherAPIView, TeacherVerifySmsCodeAPIView,
    ClassListView, TeacherLoginAPIView, TeacherProfileAPIView, UpdateStudentFieldAPIView

)
urlpatterns = [
    ###################################################################################
    #########################  STUDENT  ################################################
    ###################################################################################
    path('student/register/', RegisterStudentAPIView.as_view(), name='register_student'),
    path('student/register-verify-sms/', StudentVerifySmsCodeAPIView.as_view(), name='verify_sms'),#register
    path('student/login/', LoginAPIView.as_view(), name='login'),
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
    #########################  CLASS   ################################################
    ###################################################################################
    path('class/class_name_listview/', ClassListView.as_view(), name='class_name_listview'),




]




