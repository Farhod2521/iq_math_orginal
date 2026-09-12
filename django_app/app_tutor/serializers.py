from rest_framework import serializers
from django_app.app_management.models import  Coupon_Tutor_Student, Referral_Tutor_Student
from django_app.app_user.models import Student
from .models import TutorReferralTransaction, TutorCouponTransaction, TutorWithdrawal, TutorGroup
from .helpers import get_tutor_student_ids




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
            raise serializers.ValidationError({"error": "Foydalanuvchi o'qituvchi emas"})

        # Har bir o'qituvchiga faqat bitta kupon
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
        fields = ['id']  # foydalanuvchi 'code" yubormaydi, avtomatik generatsiya bo'ladi"

    def validate(self, attrs):
        request = self.context.get('request')

        if not request or not hasattr(request, 'user') or request.user.is_anonymous:
            raise serializers.ValidationError({"error": "Foydalanuvchi aniqlanmadi"})

        tutor = getattr(request.user, 'tutor_profile', None)
        if tutor is None:
            raise serializers.ValidationError({"error": "Foydalanuvchi o'qituvchi emas"})

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

class TutorWithdrawalSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%d/%m/%Y %H:%M")

    class Meta:
        model = TutorWithdrawal
        fields = ['id', 'amount', 'status', 'created_at']


class TutorStudentBriefSerializer(serializers.ModelSerializer):
    """Guruh ichida yoki ro'yxatda ko'rsatiladigan qisqa o'quvchi ma'lumoti."""
    phone = serializers.CharField(source='user.phone', read_only=True)
    class_uz = serializers.SerializerMethodField()
    class_ru = serializers.SerializerMethodField()
    group_id = serializers.SerializerMethodField()
    group_name = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            'id', 'full_name', 'identification', 'phone',
            'class_uz', 'class_ru', 'region', 'districts',
            'group_id', 'group_name',
        ]

    def get_class_uz(self, obj):
        if not obj.class_name:
            return None
        if obj.class_name.classes:
            return f"{obj.class_name.classes.name}-sinf {obj.class_name.name_uz}"
        return obj.class_name.name_uz

    def get_class_ru(self, obj):
        if not obj.class_name:
            return None
        if obj.class_name.classes:
            return f"{obj.class_name.classes.name}-класс {obj.class_name.name_ru}"
        return obj.class_name.name_ru

    def _tutor_group(self, obj):
        tutor = self.context.get('tutor')
        if not tutor:
            return None
        return next((g for g in obj.tutor_groups.all() if g.tutor_id == tutor.id), None)

    def get_group_id(self, obj):
        group = self._tutor_group(obj)
        return group.id if group else None

    def get_group_name(self, obj):
        group = self._tutor_group(obj)
        return group.name if group else None


class TutorGroupListSerializer(serializers.ModelSerializer):
    student_count = serializers.IntegerField(source='students.count', read_only=True)
    created_at = serializers.DateTimeField(format="%d/%m/%Y %H:%M", read_only=True)
    average_score = serializers.SerializerMethodField()

    class Meta:
        model = TutorGroup
        fields = ['id', 'name', 'description', 'is_active', 'student_count', 'average_score', 'created_at']

    def get_average_score(self, obj):
        """View'da bitta so'rovda hisoblangan xarita orqali (N+1 bo'lmasligi uchun)."""
        return self.context.get('average_map', {}).get(obj.id, 0.0)


class TutorGroupDetailSerializer(TutorGroupListSerializer):
    students = TutorStudentBriefSerializer(many=True, read_only=True)

    class Meta(TutorGroupListSerializer.Meta):
        fields = TutorGroupListSerializer.Meta.fields + ['students']


class TutorGroupWriteSerializer(serializers.ModelSerializer):
    """Guruh yaratish/tahrirlash. student_ids — ixtiyoriy, guruh tarkibini to'liq almashtiradi."""
    student_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, write_only=True, allow_empty=True
    )

    class Meta:
        model = TutorGroup
        fields = ['id', 'name', 'description', 'is_active', 'student_ids']

    def validate_name(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError("Guruh nomi bo'sh bo'lishi mumkin emas")

        tutor = self.context['tutor']
        qs = TutorGroup.objects.filter(tutor=tutor, name__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Bunday nomli guruh allaqachon mavjud")
        return value

    def validate_student_ids(self, value):
        tutor = self.context['tutor']
        allowed_ids = get_tutor_student_ids(tutor)
        invalid_ids = [student_id for student_id in value if student_id not in allowed_ids]
        if invalid_ids:
            raise serializers.ValidationError(
                f"Bu o'quvchilar sizning o'quvchilaringiz emas: {invalid_ids}"
            )
        return value

    def create(self, validated_data):
        student_ids = validated_data.pop('student_ids', [])
        group = TutorGroup.objects.create(tutor=self.context['tutor'], **validated_data)
        if student_ids:
            set_group_students(group, student_ids)
        return group

    def update(self, instance, validated_data):
        student_ids = validated_data.pop('student_ids', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if student_ids is not None:
            set_group_students(group=instance, student_ids=student_ids)
        return instance


def set_group_students(group, student_ids):
    """
    Guruh tarkibini belgilaydi. Bir o'quvchi bitta tutorning faqat bitta guruhida
    bo'lishi kerak, shuning uchun u tutorning boshqa guruhlaridan olib tashlanadi.
    """
    students = Student.objects.filter(id__in=student_ids)
    for other_group in TutorGroup.objects.filter(tutor=group.tutor).exclude(pk=group.pk):
        other_group.students.remove(*students)
    group.students.set(students)
