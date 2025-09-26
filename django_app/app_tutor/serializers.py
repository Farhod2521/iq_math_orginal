from rest_framework import serializers
from django_app.app_management.models import  Coupon_Tutor_Student, Referral_Tutor_Student

class CouponCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon_Tutor_Student  # yoki siz ishlatayotgan model
        fields = ['code']

    def validate_code(self, value):
        if Coupon_Tutor_Student.objects.filter(code=value).exists():
            raise serializers.ValidationError("Bu kupon kodi allaqachon mavjud")
        return value
    

class ReferralCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Referral_Tutor_Student
        fields = ['code']

    def validate_code(self, value):
        if Referral_Tutor_Student.objects.filter(code=value).exists():
            raise serializers.ValidationError("Bu referal kodi allaqachon mavjud")
        return value