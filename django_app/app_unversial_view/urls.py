from django.urls import path
from .cuoponView import UniversalCouponAPIView, UniversalCouponTransactionAPIView

urlpatterns = [
    path('coupon-generate/', UniversalCouponAPIView.as_view(), name='coupon-generate'),
    path('coupon-transaction/', UniversalCouponTransactionAPIView.as_view(), name='coupon-generate'),
]
