# urls.py
from django.urls import path
from .views import PaymentCallbackAPIView, InitiatePaymentAPIView

urlpatterns = [
    path("payment-callback/", PaymentCallbackAPIView.as_view(), name="payment-callback"),
    path("initiate-payment/", InitiatePaymentAPIView.as_view(), name="initiate-payment"),
]
