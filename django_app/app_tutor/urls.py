from django.urls import path
from .views import TutorCreateCouponAPIView

urlpatterns = [
    path('tutor/create-coupon/', TutorCreateCouponAPIView.as_view(), name='tutor-create-coupon'),
]