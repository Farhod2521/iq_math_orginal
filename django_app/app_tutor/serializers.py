from rest_framework import serializers
from django_app.app_management.models import  Coupon_Tutor_Student, Referral_Tutor_Student
from .models import TutorReferralTransaction, TutorCouponTransaction




class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon_Tutor_Student
        fields = ['id', 'code', 'discount_percent', 'valid_from', 'valid_until', 'is_active']


class ReferralSerializer(serializers.ModelSerializer):
    class Meta:
        model = Referral_Tutor_Student
        fields = ['id', 'code', 'bonus_percent', 'valid_from', 'valid_until', 'is_active']

class CouponCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon_Tutor_Student
        # 'code' foydalanuvchi tomonidan yuborilmaydi — viewsetda avtomatik yaratiladi
        fields = ['id']  

    def validate(self, attrs):
        request = self.context.get('request')

        if not request or not hasattr(request, 'user') or request.user.is_anonymous:
            raise serializers.ValidationError({"error": "Foydalanuvchi aniqlanmadi"})

        tutor = getattr(request.user, 'tutor_profile', None)
        if tutor is None:
            raise serializers.ValidationError({"error": "Foydalanuvchi o‘qituvchi emas"})

        # Har bir o‘qituvchiga faqat bitta kupon
        if Coupon_Tutor_Student.objects.filter(created_by_tutor=tutor).exists():
            raise serializers.ValidationError({"error": "Siz allaqachon kupon yaratgansiz"})

        attrs['created_by_tutor'] = tutor
        return attrs

    def create(self, validated_data):
        # Kupon kodi viewset ichida generate qilinadi
        return Coupon_Tutor_Student.objects.create(**validated_data)

class ReferralCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Referral_Tutor_Student
        fields = ['id']  # foydalanuvchi 'code' yubormaydi, avtomatik generatsiya bo‘ladi

    def validate(self, attrs):
        request = self.context.get('request')

        if not request or not hasattr(request, 'user') or request.user.is_anonymous:
            raise serializers.ValidationError({"error": "Foydalanuvchi aniqlanmadi"})

        tutor = getattr(request.user, 'tutor_profile', None)
        if tutor is None:
            raise serializers.ValidationError({"error": "Foydalanuvchi o‘qituvchi emas"})

        # faqat bitta referal linkga ruxsat
        if Referral_Tutor_Student.objects.filter(created_by_tutor=tutor).exists():
            raise serializers.ValidationError({"error": "Siz allaqachon referal link yaratgansiz"})

        attrs['created_by_tutor'] = tutor
        return attrs

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
    used_at = serializers.DateTimeField(format="%d/%m/%Y %H:%M", read_only=True)  # ✅ sana formatlash

    class Meta:
        model = TutorReferralTransaction
        fields = [
            'id', 'student', 'student_name',
            'payment_amount', 'bonus_amount', 'used_at'
        ]