from django.urls import path
from .cuoponView import UniversalCouponAPIView, UniversalCouponTransactionAPIView
from .universal_statistics import UniversalStatisticsAPIView

urlpatterns = [
    path('coupon-generate/', UniversalCouponAPIView.as_view(), name='coupon-generate'),
    path('coupon-generate/<int:pk>/', UniversalCouponAPIView.as_view(), name='coupon-generate'),
    path('coupon-transaction/', UniversalCouponTransactionAPIView.as_view(), name='coupon-transaction'),
    path('statistics/<int:pk>/', UniversalStatisticsAPIView.as_view(), name='universal-statistics'),
]
