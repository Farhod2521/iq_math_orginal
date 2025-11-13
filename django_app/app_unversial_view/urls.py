from django.urls import path
from .cuoponView import UniversalCouponAPIView

urlpatterns = [
    path('coupon-generate/', UniversalCouponAPIView.as_view(), name='coupon-generate'),
]
