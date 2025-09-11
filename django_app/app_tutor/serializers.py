from rest_framework import serializers
from django_app.app_management.models import  Coupon

class CouponCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = ['code']  # tutor faqat code kiritadi