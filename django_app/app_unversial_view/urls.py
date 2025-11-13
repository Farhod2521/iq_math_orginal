from django.urls import path
from  .cuoponView import  UniversalCouponViewSet


urlpatterns = [
    path('coupon-generate/', UniversalCouponViewSet.as_view(), name='tutor-coupon-transactions'),


]