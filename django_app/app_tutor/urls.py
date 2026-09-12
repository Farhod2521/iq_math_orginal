from django.urls import path
from .views import (
TutorCouponTransactionListAPIView, TutorReferralTransactionListAPIView,
TutorCouponViewSet, TutorReferralViewSet, TutorEarningsAPIView, TutorWithdrawalCreateAPIView,
TutorWithdrawalListAPIView, TutorDetailAPIView
)
from .withdrawal_settings_crud import WithdrawalLimitSettingsCRUDAPIView
from .group_views import (
    TutorGroupListCreateAPIView, TutorGroupDetailAPIView,
    TutorGroupStudentsAPIView, TutorStudentListAPIView
)
from .results_views import (
    TutorStudentsResultsAPIView, TutorStudentResultDetailAPIView,
    TutorGroupResultsAPIView, TutorResultsOverviewAPIView, TutorResultsChartAPIView
)


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

    # === Guruhlar ===
    path('tutor/groups/', TutorGroupListCreateAPIView.as_view(), name='tutor-group-list-create'),
    path('tutor/groups/<int:pk>/', TutorGroupDetailAPIView.as_view(), name='tutor-group-detail'),
    path('tutor/groups/<int:pk>/students/', TutorGroupStudentsAPIView.as_view(), name='tutor-group-students'),
    path('tutor/groups/<int:pk>/results/', TutorGroupResultsAPIView.as_view(), name='tutor-group-results'),

    # === O'quvchilar va natijalar ===
    path('tutor/my-students/', TutorStudentListAPIView.as_view(), name='tutor-my-students'),
    path('tutor/results/overview/', TutorResultsOverviewAPIView.as_view(), name='tutor-results-overview'),
    path('tutor/results/chart/', TutorResultsChartAPIView.as_view(), name='tutor-results-chart'),
    path('tutor/results/students/', TutorStudentsResultsAPIView.as_view(), name='tutor-results-students'),
    path('tutor/results/students/<int:student_id>/', TutorStudentResultDetailAPIView.as_view(), name='tutor-results-student-detail'),

    # SuperAdmin — WithdrawalLimitSettings CRUD
    path('superadmin/withdrawal-settings/', WithdrawalLimitSettingsCRUDAPIView.as_view(), name='withdrawal-settings-list'),
    path('superadmin/withdrawal-settings/<int:pk>/', WithdrawalLimitSettingsCRUDAPIView.as_view(), name='withdrawal-settings-detail'),
]+ router.urls