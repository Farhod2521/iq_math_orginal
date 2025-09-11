# urls.py
from django.urls import path
from .views import (
    PaymentCallbackAPIView, InitiatePaymentAPIView, 
    SubscriptionTrialDaysAPIView, MyPaymentsAPIView, CheckCouponAPIView, SubscriptionPlanListAPIView
)

urlpatterns = [
    path("payment-callback/", PaymentCallbackAPIView.as_view(), name="payment-callback"),
    path("initiate-payment/", InitiatePaymentAPIView.as_view(), name="initiate-payment"),
    path("subscription/trial_days/", SubscriptionTrialDaysAPIView.as_view(), name="initiate-payment"),
    path('my-payments/', MyPaymentsAPIView.as_view(), name='my-payments'),
    path('check-coupon/', CheckCouponAPIView.as_view(), name='my-payments'),
    path('plans/', SubscriptionPlanListAPIView.as_view(), name='subscription-plan-list'),
]
