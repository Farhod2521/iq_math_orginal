from rest_framework import serializers
from django_app.app_management.models import  Coupon_Tutor_Student, Referral_Tutor_Student

class CouponCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon_Tutor_Student
        fields = ['code']

    def validate(self, attrs):
        request = self.context.get('request')
        tutor = getattr(request.user, 'tutor', None)
        if tutor is None:
            raise serializers.ValidationError({"error": "Foydalanuvchi o‘qituvchi emas"})

        # agar bu tutor allaqachon kupon yaratgan bo‘lsa
        if Coupon_Tutor_Student.objects.filter(created_by_tutor=tutor).exists():
            raise serializers.ValidationError({"error": "Siz allaqachon kupon yaratgansiz"})
        return attrs

    def validate_code(self, value):
        if Coupon_Tutor_Student.objects.filter(code=value).exists():
            raise serializers.ValidationError("Bu kupon kodi allaqachon mavjud")
        return value
class ReferralCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Referral_Tutor_Student
        fields = ['code']

    def validate(self, attrs):
        request = self.context.get('request')
        tutor = getattr(request.user, 'tutor', None)
        if tutor is None:
            raise serializers.ValidationError({"error": "Foydalanuvchi o‘qituvchi emas"})

        # agar bu tutor allaqachon referal link yaratgan bo‘lsa
        if Referral_Tutor_Student.objects.filter(created_by_tutor=tutor).exists():
            raise serializers.ValidationError({"error": "Siz allaqachon referal link yaratgansiz"})
        return attrs

    def validate_code(self, value):
        if Referral_Tutor_Student.objects.filter(code=value).exists():
            raise serializers.ValidationError("Bu referal kodi allaqachon mavjud")
        return value