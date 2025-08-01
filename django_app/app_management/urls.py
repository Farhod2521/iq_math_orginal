from django.urls import path
from .views import SystemSettingsListView, FAQListView, ProductListView, StatisticsAPIView, BannerListView

urlpatterns = [
    path('system-settings/', SystemSettingsListView.as_view(), name='system-settings-list'),
    path('banner/', BannerListView.as_view(), name='system-settings-list'),
    path('faqs/', FAQListView.as_view(), name='faq-list'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('statistics/', StatisticsAPIView.as_view(), name='statistics'),
]
