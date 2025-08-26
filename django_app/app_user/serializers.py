from rest_framework import serializers
from .models import User, Student, UserSMSAttempt, Class, Teacher, Subject, Referral, Parent
from django.core.cache import cache
import random
from .sms_service import send_sms, send_verification_email, send_login_parol_email# SMS sending function
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from django.utils.timezone import now
from django_app.app_payments.models import Subscription, SubscriptionSetting
from django_app.app_student.models import  StudentScore, StudentReferral
from django_app.app_management.models import  ReferralAndCouponSettings
User = get_user_model()

from datetime import timedelta


class StudentProfileSerializer(serializers.Serializer):
    class Meta:
        model  =  Student
        fields = "__all__"

def check_login_attempts(phone):
    """Login urinishlarini tekshiradi va bloklash uchun hisoblaydi."""
    cache_key = f"login_attempts_{phone}"
    attempts = cache.get(cache_key, 0)

    if attempts >= 5:
        return False  # 5 martadan keyin bloklanadi

    cache.set(cache_key, attempts + 1, timeout=600)  # 15 daqiqa ichida 5 martadan ortiq bo‘lsa bloklash
    return True

def reset_login_attempts(phone):
    """Agar foydalanuvchi to‘g‘ri kirsa, urinishlar sonini 0 ga tushiramiz."""
    cache.delete(f"login_attempts_{phone}")
class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField(required=True)
    password = serializers.CharField(required=True)

 

    def validate(self, data):
        phone = data.get('phone')
        password = data.get('password')

        # Foydalanuvchi bloklanganligini tekshirish
        if not check_login_attempts(phone):
            raise serializers.ValidationError("Ko‘p noto‘g‘ri urinishlar! 5 daqiqa kuting.")

        # Foydalanuvchini autentifikatsiya qilish
        user = authenticate(phone=phone, password=password)

        if user is None:
            raise serializers.ValidationError("Telefon raqam yoki parol noto'g'ri.")

        # Login urinishlarini reset qilish
        reset_login_attempts(phone)

        return {"user": user}
    



##############################################################
###################     TEACHER    REGISTER   ################
##############################################################   
class TeacherRegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    phone = serializers.CharField(required=True)



    def validate_user_data(self, email, phone):
        """Foydalanuvchi ma'lumotlarini tekshirish"""
        user = User.objects.filter(phone=phone).first()
        if user:
            teacher = getattr(user, "teacher_profile", None)
            if teacher and not teacher.status:
                # 5 daqiqa ichida qayta urinishni tekshirish
                time_diff = now() - teacher.teacher_date
                remaining_time = 300 - int(time_diff.total_seconds())

                if remaining_time > 0:
                    minutes = remaining_time // 60
                    seconds = remaining_time % 60
                    raise serializers.ValidationError(
                        f"Qayta urinib ko‘rish uchun {minutes} daqiqa {seconds} soniya kuting."
                    )

                # 5 daqiqadan keyin userni o‘chirish
                user.delete()
            else:
                raise serializers.ValidationError("Bu telefon raqam allaqachon ro'yxatdan o'tgan.")

        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("Bu email allaqachon ro'yxatdan o'tgan.")

    def validate(self, attrs):
        """Barcha tekshiruvlarni yagona joyda bajarish"""
        self.validate_user_data(attrs.get("email"), attrs.get("phone"))

        if Teacher.objects.filter(document=attrs.get("document")).exists():
            raise serializers.ValidationError("Bu shaxs allaqachon ro'yxatdan o'tgan.")

        return attrs

    def create(self, validated_data):
        phone = validated_data['phone']
        email = validated_data['email']


        teacher_data = {
            "full_name": validated_data.pop("full_name"),
            "status": False,
            "teacher_date": now()
        }

        # Yangi foydalanuvchi yaratish
        user = User.objects.create(phone=phone, email=email, role="teacher")

        # SMS kod yaratish
        sms_code = str(random.randint(10000, 99999))
        user.sms_code = sms_code
        user.set_unusable_password()
        user.save()

        # Teacher ma'lumotlarini saqlash
        teacher_data["user"] = user
        teacher = Teacher.objects.create(**teacher_data)


        # SMS yuborish
        send_sms(phone, sms_code)

        return user



##############################################################
###################     STUNDENT    REGISTER   ###############
##############################################################
class StudentRegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=True)
    phone = serializers.CharField(required=True)
    class_name = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all(), required=True)
    referral_code = serializers.CharField(required=False, allow_blank=True)

    def validate_user_data(self, phone):
        user = User.objects.filter(phone=phone).first()
        if user:
            student = getattr(user, "student_profile", None)
            if student and not student.status:
                # 5 daqiqalik limit
                time_diff = now() - student.student_date
                remaining_time = 300 - int(time_diff.total_seconds())

                if remaining_time > 0:
                    minutes = remaining_time // 60
                    seconds = remaining_time % 60
                    raise serializers.ValidationError(
                        f"Qayta urinib ko‘rish uchun {minutes} daqiqa {seconds} soniya kuting."
                    )
                user.delete()
            else:
                raise serializers.ValidationError("Bu telefon raqam allaqachon ro'yxatdan o'tgan.")

    def validate(self, attrs):
        self.validate_user_data(attrs.get("phone"))
        return attrs

    def create(self, validated_data):
        phone = validated_data['phone']
        class_name = validated_data.pop('class_name')
        referral_code = validated_data.pop('referral_code', None)

        student_data = {
            'full_name': validated_data.pop('full_name'),
            'class_name': class_name,
            'status': False,
            'student_date': now()
        }

        # 1. User yaratish
        user = User.objects.create(phone=phone, role='student')

        # 2. SMS code
        sms_code = str(random.randint(10000, 99999))
        user.sms_code = sms_code
        user.set_unusable_password()
        user.save()

        # 3. Student yaratish
        student_data['user'] = user
        student = Student.objects.create(**student_data)

        # 4. Obuna
        free_days = SubscriptionSetting.objects.first().free_trial_days
        Subscription.objects.create(
            student=student,
            start_date=now(),
            end_date=now() + timedelta(days=free_days),
            is_paid=False
        )

        # 5. Faqat referral yozuvi (ball YO‘Q!)
        if referral_code:
            try:
                referrer_student = Student.objects.get(identification=referral_code)
                StudentReferral.objects.create(referrer=referrer_student, referred=student)
            except Student.DoesNotExist:
                pass

        # 6. SMS yuborish
        send_sms(phone, sms_code)

        return user

        
class Class_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Class
        fields = ['id', 'name']

import random
import string

class VerifySmsCodeSerializer(serializers.Serializer):
    phone = serializers.CharField(required=True)
    sms_code = serializers.CharField(required=True)

    def validate(self, data):
        phone = data.get('phone')
        sms_code = data.get('sms_code')

        try:
            user = User.objects.get(phone=phone, sms_code=sms_code)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                "non_field_errors": ["Telefon raqam yoki kod noto'g'ri."]
            })

        # Random parol generatsiya
        chars = string.ascii_letters + string.digits
        password = ''.join(random.choice(chars) for _ in range(8))

        user.set_password(password)
        user.sms_code = None
        user.save()

        # Parolni emailga yuborish
        if user.email:
            send_login_parol_email(user.email, phone, password)

        try:
            student = Student.objects.get(user=user)
            student.status = True
            student.save()

            # ✳️ Referral bo‘lsa ball beriladi
            try:
                referral = StudentReferral.objects.get(referred=student)
                referrer = referral.referrer

                settings = ReferralAndCouponSettings.objects.first()
                student_bonus = settings.student_referral_bonus_points
                referrer_bonus = settings.student_referral_bonus_points

                # Referrer uchun
                ref_score, _ = StudentScore.objects.get_or_create(student=referrer)
                ref_score.score += referrer_bonus
                ref_score.save()

                # Referred uchun
                my_score, _ = StudentScore.objects.get_or_create(student=student)
                my_score.score += student_bonus
                my_score.save()

            except StudentReferral.DoesNotExist:
                pass

        except Student.DoesNotExist:
            raise serializers.ValidationError({
                "non_field_errors": ["Student profili topilmadi."]
            })

        return {"phone": phone, "password": password, "user": user}


class TeacherVerifySmsCodeSerializer(serializers.Serializer):
    phone = serializers.CharField(required=True)
    sms_code = serializers.CharField(required=True)

    def validate(self, data):
        phone = data.get('phone')
        sms_code = data.get('sms_code')

        try:
            user = User.objects.get(phone=phone, sms_code=sms_code)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                "non_field_errors": ["Telefon raqam yoki kod noto'g'ri."]
            })

        # Generate a random password
        chars = string.ascii_letters + string.digits
        password = ''.join(random.choice(chars) for _ in range(8))

        # Set the password for the user
        user.set_password(password)
        user.sms_code = None  # Clear the SMS code
        user.save()
        email = user.email
        send_login_parol_email(email, phone,password)
        # Update student status to True
        try:
            teacher = Teacher.objects.get(user=user)
            teacher.status = True
            teacher.save()
        except teacher.DoesNotExist:
            raise serializers.ValidationError({
                "non_field_errors": ["teacher profili topilmadi."]
            })

        return {"phone": phone, "password": password, "user": user}
    


class TeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teacher
        fields = '__all__'

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = '__all__'



from django.contrib.auth.hashers import make_password

class ParentCreateSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)
    students = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all(), many=True)

    class Meta:
        model = Parent
        fields = ['full_name', 'phone', 'password', 'students']

    def create(self, validated_data):
        phone = validated_data.pop('phone')
        password = validated_data.pop('password')
        students = validated_data.pop('students')

        # Yangi User yaratish
        user = User.objects.create(
            phone=phone,
            role='parent',
            password=make_password(password)  # parolni hash qilish
        )

        parent = Parent.objects.create(user=user, **validated_data)
        parent.students.set(students)
        return parent