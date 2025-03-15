from django.urls import path
from .views import (
      VerifySmsCodeAPIView, LoginAPIView, 
     StudentProfileAPIView, StudentsListView, ForgotPasswordView, VerifySMSCodeView,
    ResetPasswordView, ResendSMSCodeView,
    LogoutDeviceAPIView

)
urlpatterns = [
    path('verify-sms/', VerifySmsCodeAPIView.as_view(), name='verify_sms'),#register
    path('login/', LoginAPIView.as_view(), name='login'),
    path('profile/', StudentProfileAPIView.as_view(), name='profile'),
    path('student_list/', StudentsListView.as_view(), name='student_list'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('verify-sms-code/', VerifySMSCodeView.as_view(), name='verify-sms-code'),###foget-pasword
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('resend-sms-code/', ResendSMSCodeView.as_view(), name='resend-sms-code'), 
    path('logout_device/', LogoutDeviceAPIView.as_view(), name='logout_device'), 

]




