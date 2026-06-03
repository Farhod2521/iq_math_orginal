from django.urls import path
from .views import (
TutorCouponTransactionListAPIView, TutorReferralTransactionListAPIView,
TutorCouponViewSet, TutorReferralViewSet, TutorEarningsAPIView, TutorWithdrawalCreateAPIView,
TutorWithdrawalListAPIView, TutorDetailAPIView
)
from .withdrawal_settings_crud import WithdrawalLimitSettingsCRUDAPIView


from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'tutor/coupons', TutorCouponViewSet, basename='tutor-coupon')
router.register(r'tutor/referrals', TutorReferralViewSet, basename='tutor-referral')


urlpatterns = [
    path('tutor/<int:pk>/detail/', TutorDetailAPIView.as_view(), name='tutor-detail'),
    path('tutor/coupon-transactions/', TutorCouponTransactionListAPIView.as_view(), name='tutor-coupon-transactions'),
    path('tutor/referral-transactions/', TutorReferralTransactionListAPIView.as_view(), name='tutor-referral-transactions'),
    path('tutor/payments/', TutorEarningsAPIView.as_view(), name='tutor-earnings'),
    path('tutor/withdraw/', TutorWithdrawalCreateAPIView.as_view(), name='tutor-withdraw'),
    path('tutor/withdrawals/list/', TutorWithdrawalListAPIView.as_view(), name='tutor-withdrawal-list'),

    # SuperAdmin — WithdrawalLimitSettings CRUD
    path('superadmin/withdrawal-settings/', WithdrawalLimitSettingsCRUDAPIView.as_view(), name='withdrawal-settings-list'),
    path('superadmin/withdrawal-settings/<int:pk>/', WithdrawalLimitSettingsCRUDAPIView.as_view(), name='withdrawal-settings-detail'),
]+ router.urls