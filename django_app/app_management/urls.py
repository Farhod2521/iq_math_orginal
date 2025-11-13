from django.urls import path
from .views import SystemSettingsListView, FAQListView, ProductListView, FullStatisticsAPIView, BannerListView, MotivationAPIView, ElonListAPIView

urlpatterns = [
    path('system-settings/', SystemSettingsListView.as_view(), name='system-settings-list'),
    path('banner/', BannerListView.as_view(), name='system-settings-list'),
    path('faqs/', FAQListView.as_view(), name='faq-list'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('statistics/', FullStatisticsAPIView.as_view(), name='statistics'),


    ######################  MOBILE APP ####################################
    path('app/motivation-list/', MotivationAPIView.as_view(), name='statistics'),
    path('app/elon-list/', ElonListAPIView.as_view(), name='statistics'),

]
