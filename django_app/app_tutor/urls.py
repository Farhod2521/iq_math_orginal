from django.urls import path
from .views import TutorCreateCouponAPIView, TutorCreateReferralAPIView

urlpatterns = [
    path('tutor/create-coupon/', TutorCreateCouponAPIView.as_view(), name='tutor-create-coupon'),
    path('tutor/create-referral/', TutorCreateReferralAPIView.as_view(), name='tutor-create-coupon'),
]