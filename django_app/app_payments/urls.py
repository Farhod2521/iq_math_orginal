# urls.py
from django.urls import path
from .views import PaymentCallbackAPIView

urlpatterns = [
    path("api/payment-callback/", PaymentCallbackAPIView.as_view(), name="payment-callback"),
]
