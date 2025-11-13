




from rest_framework import serializers
from django_app.app_management.models import  Coupon_Tutor_Student

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
    

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon_Tutor_Student
        fields = ['id', 'code', 'discount_percent', 'valid_from', 'valid_until', 'is_active']
