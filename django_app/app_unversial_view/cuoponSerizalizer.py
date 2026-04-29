




from rest_framework import serializers
from django.utils import timezone
from django_app.app_management.models import Coupon_Tutor_Student

class CouponCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon_Tutor_Student
        fields = ['id']

    def validate(self, attrs):
        request = self.context.get('request')

        if not request or request.user.is_anonymous:
            raise serializers.ValidationError({"error": "Foydalanuvchi aniqlanmadi"})

        user = request.user
        now_time = timezone.now()

        # Student
        if user.role == 'student':
            student = user.student_profile
            qs = Coupon_Tutor_Student.objects.filter(created_by_student=student)
            qs.filter(valid_until__lt=now_time).delete()
            if qs.filter(is_active=True).exists():
                raise serializers.ValidationError({"error": "Sizning faol kuponingiz mavjud"})
            attrs['created_by_student'] = student

        # Tutor
        elif user.role == 'tutor':
            tutor = user.tutor_profile
            qs = Coupon_Tutor_Student.objects.filter(created_by_tutor=tutor)
            qs.filter(valid_until__lt=now_time).delete()
            if qs.filter(is_active=True).exists():
                raise serializers.ValidationError({"error": "Sizning faol kuponingiz mavjud"})
            attrs['created_by_tutor'] = tutor

        # Teacher
        elif user.role == 'teacher':
            attrs['created_by_teacher'] = user.teacher_profile

        else:
            raise serializers.ValidationError({"error": "Bu rolda kupon yaratish mumkin emas"})

        return attrs

    def create(self, validated_data):
        return Coupon_Tutor_Student.objects.create(**validated_data)

    

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon_Tutor_Student
        fields = ['id', 'code', 'discount_percent', 'valid_from', 'valid_until', 'is_active']


class CouponTransactionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    student = serializers.CharField()
    owner = serializers.CharField()
    coupon = serializers.CharField()
    payment_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    cashback_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    used_at = serializers.DateTimeField()
    type = serializers.CharField()