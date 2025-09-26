from django.urls import path
from .views import  TutorCouponTransactionListAPIView, TutorReferralTransactionListAPIView, TutorCouponViewSet, TutorReferralViewSet


from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'tutor/coupons', TutorCouponViewSet, basename='tutor-coupon')
router.register(r'tutor/referrals', TutorReferralViewSet, basename='tutor-referral')


urlpatterns = [
    path('tutor/coupon-transactions/', TutorCouponTransactionListAPIView.as_view(), name='tutor-coupon-transactions'),
    path('tutor/referral-transactions/', TutorReferralTransactionListAPIView.as_view(), name='tutor-referral-transactions'),
]+ router.urls