from rest_framework import serializers
from django_app.app_management.models import  Coupon_Tutor_Student, Referral_Tutor_Student
from .models import TutorReferralTransaction, TutorCouponTransaction




class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon_Tutor_Student
        fields = ['id',  'discount_percent', 'valid_from', 'valid_until', 'is_active']


class ReferralSerializer(serializers.ModelSerializer):
    class Meta:
        model = Referral_Tutor_Student
        fields = ['id', 'code', 'bonus_percent', 'valid_from', 'valid_until', 'is_active']

class CouponCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon_Tutor_Student
        fields = ['code']

    def validate(self, attrs):
        request = self.context.get('request')

        if not request or not hasattr(request, 'user') or request.user.is_anonymous:
            raise serializers.ValidationError({"error": "Foydalanuvchi aniqlanmadi"})

        tutor = getattr(request.user, 'tutor_profile', None)
        if tutor is None:
            raise serializers.ValidationError({"error": "Foydalanuvchi o‘qituvchi emas"})

        if Coupon_Tutor_Student.objects.filter(created_by_tutor=tutor).exists():
            raise serializers.ValidationError({"error": "Siz allaqachon kupon yaratgansiz"})

        attrs['created_by_tutor'] = tutor
        return attrs

    def validate_code(self, value):
        if Coupon_Tutor_Student.objects.filter(code=value).exists():
            raise serializers.ValidationError("Bu kupon kodi allaqachon mavjud")
        return value

    def create(self, validated_data):
        return Coupon_Tutor_Student.objects.create(**validated_data)


class ReferralCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Referral_Tutor_Student
        fields = ['code']

    def validate(self, attrs):
        request = self.context.get('request')

        if not request or not hasattr(request, 'user') or request.user.is_anonymous:
            raise serializers.ValidationError({"error": "Foydalanuvchi aniqlanmadi"})

        tutor = getattr(request.user, 'tutor_profile', None)
        if tutor is None:
            raise serializers.ValidationError({"error": "Foydalanuvchi o‘qituvchi emas"})

        if Referral_Tutor_Student.objects.filter(created_by_tutor=tutor).exists():
            raise serializers.ValidationError({"error": "Siz allaqachon referal link yaratgansiz"})

        attrs['created_by_tutor'] = tutor
        return attrs

    def validate_code(self, value):
        if Referral_Tutor_Student.objects.filter(code=value).exists():
            raise serializers.ValidationError("Bu referal kodi allaqachon mavjud")
        return value

    def create(self, validated_data):
        return Referral_Tutor_Student.objects.create(**validated_data)


class TutorCouponTransactionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    coupon_code = serializers.CharField(source='coupon.code', read_only=True)

    class Meta:
        model = TutorCouponTransaction
        fields = [
            'id', 'student', 'student_name', 'coupon', 'coupon_code',
            'payment_amount', 'cashback_amount', 'used_at'
        ]


class TutorReferralTransactionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    referral_code = serializers.CharField(source='referral.code', read_only=True)

    class Meta:
        model = TutorReferralTransaction
        fields = [
            'id', 'student', 'student_name', 'referral', 'referral_code',
            'payment_amount', 'bonus_amount', 'used_at'
        ]