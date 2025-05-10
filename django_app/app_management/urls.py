from django.urls import path
from .views import SystemSettingsListView, FAQListView

urlpatterns = [
    path('api/system-settings/', SystemSettingsListView.as_view(), name='system-settings-list'),
    path('api/faqs/', FAQListView.as_view(), name='faq-list'),
]
