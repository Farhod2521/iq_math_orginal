




from rest_framework import serializers
from django_app.app_management.models import  Coupon_Tutor_Student

class CouponCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon_Tutor_Student
        fields = ['id']  # Foydalanuvchi hech narsa yubormaydi

    def validate(self, attrs):
        request = self.context.get('request')

        if not request or request.user.is_anonymous:
            raise serializers.ValidationError({"error": "Foydalanuvchi aniqlanmadi"})

        user = request.user

        # Student
        if user.role == 'student':
            student = user.student_profile
            if Coupon_Tutor_Student.objects.filter(created_by_student=student).exists():
                raise serializers.ValidationError({"error": "Siz allaqachon kupon yaratgansiz"})
            attrs['created_by_student'] = student

        # Tutor
        elif user.role == 'tutor':
            tutor = user.tutor_profile
            if Coupon_Tutor_Student.objects.filter(created_by_tutor=tutor).exists():
                raise serializers.ValidationError({"error": "Siz allaqachon kupon yaratgansiz"})
            attrs['created_by_tutor'] = tutor

        # Teacher
        elif user.role == 'teacher':
            teacher = user.teacher_profile
            if Coupon_Tutor_Student.objects.filter(created_by_teacher=teacher).exists():
                raise serializers.ValidationError({"error": "Siz allaqachon kupon yaratgansiz"})
            attrs['created_by_teacher'] = teacher

        else:
            raise serializers.ValidationError({"error": "Bu rolda kupon yaratish mumkin emas"})

        return attrs

    def create(self, validated_data):
        return Coupon_Tutor_Student.objects.create(**validated_data)

    

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon_Tutor_Student
        fields = ['id', 'code', 'discount_percent', 'valid_from', 'valid_until', 'is_active']
