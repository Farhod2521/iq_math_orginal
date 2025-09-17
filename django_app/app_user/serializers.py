from rest_framework import serializers
from .models import User, Student, UserSMSAttempt, Class, Teacher, Subject, Referral, Parent, Tutor
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
class UniversalRegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=True)
    phone = serializers.CharField(required=True)
    role = serializers.ChoiceField(choices=['student', 'parent', 'tutor'], required=True)
    class_name = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all(), required=False, allow_null=True
    )
    referral_code = serializers.CharField(required=False, allow_blank=True)

    def validate_user_data(self, phone):
        user = User.objects.filter(phone=phone).first()
        if user:
            raise serializers.ValidationError("Bu telefon raqam allaqachon ro'yxatdan o'tgan.")

    def validate(self, attrs):
        self.validate_user_data(attrs.get("phone"))
        role = attrs.get("role")

        # student bo'lsa class_name majburiy
        if role == "student" and not attrs.get("class_name"):
            raise serializers.ValidationError({"class_name": "Student uchun sinf tanlash shart."})
        return attrs

    def create(self, validated_data):
        phone = validated_data['phone']
        role = validated_data['role']
        full_name = validated_data['full_name']
        class_name = validated_data.pop('class_name', None)
        referral_code = validated_data.pop('referral_code', None)

        # 1. Mavjud userni tekshiramiz
        user = User.objects.filter(phone=phone, role=role).first()

        # SMS code generatsiya
        sms_code = str(random.randint(10000, 99999))

        if user:
            # Agar mavjud bo'lsa va status hali tasdiqlanmagan bo'lsa – sms_code yangilanadi
            if hasattr(user, 'student_profile'):
                profile = user.student_profile
                if not profile.status:  # status False
                    user.sms_code = sms_code
                    user.save(update_fields=['sms_code'])
                    send_sms(phone, sms_code)
                    return user  # qayta profil yaratmaymiz
            elif hasattr(user, 'parent_profile'):
                profile = user.parent_profile
                if not profile.status:
                    user.sms_code = sms_code
                    user.save(update_fields=['sms_code'])
                    send_sms(phone, sms_code)
                    return user
            elif hasattr(user, 'tutor_profile'):
                profile = user.tutor_profile
                if not profile.status:
                    user.sms_code = sms_code
                    user.save(update_fields=['sms_code'])
                    send_sms(phone, sms_code)
                    return user

            # Agar status True bo'lsa — demak tasdiqlangan, xatolik
            raise serializers.ValidationError("Bu telefon raqam allaqachon ro'yxatdan o'tgan.")

        # 2. Yangi User yaratish
        user = User.objects.create(phone=phone, role=role)
        user.sms_code = sms_code
        user.set_unusable_password()
        user.save()

        # 3. Role bo‘yicha profillar
        if role == "student":
            student = Student.objects.create(
                user=user,
                full_name=full_name,
                class_name=class_name,
                status=False,
                student_date=now()
            )

            # trial subscription
            free_days = SubscriptionSetting.objects.first().free_trial_days
            Subscription.objects.create(
                student=student,
                start_date=now(),
                end_date=now() + timedelta(days=free_days),
                is_paid=False
            )

            # referral
            if referral_code:
                try:
                    referrer_student = Student.objects.get(identification=referral_code)
                    StudentReferral.objects.create(referrer=referrer_student, referred=student)
                except Student.DoesNotExist:
                    pass

        elif role == "parent":
            Parent.objects.create(
                user=user,
                full_name=full_name,
                status=False  # parent ham status bilan bo‘lishi kerak
            )

        elif role == "tutor":
            Tutor.objects.create(
                user=user,
                full_name=full_name,
                status=False
            )

        # 4. SMS yuborish
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
        phone = data.get("phone")
        sms_code = data.get("sms_code")

        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                "non_field_errors": ["Bunday foydalanuvchi topilmadi."]
            })

        # Kodni solishtirish
        if not user.sms_code or str(user.sms_code) != str(sms_code):
            raise serializers.ValidationError({
                "non_field_errors": ["Telefon raqam yoki kod noto'g'ri."]
            })

        # Random parol generatsiya
        chars = string.ascii_letters + string.digits
        password = "".join(random.choice(chars) for _ in range(8))

        user.set_password(password)
        user.sms_code = None  # ❗️ Kod bir martalik
        user.save()

        # Agar email bo‘lsa login-parol yuborish
        if user.email:
            send_login_parol_email(user.email, phone, password)

        # Role bo‘yicha profil statusni yoqish
        if user.role == "student":
            student = Student.objects.filter(user=user).first()
            if not student:
                raise serializers.ValidationError({"non_field_errors": ["Student profili topilmadi."]})
            student.status = True
            student.save()

        elif user.role == "parent":
            parent = Parent.objects.filter(user=user).first()
            if not parent:
                raise serializers.ValidationError({"non_field_errors": ["Parent profili topilmadi."]})
            parent.status = True
            parent.save()

        elif user.role == "tutor":
            tutor = Tutor.objects.filter(user=user).first()
            if not tutor:
                raise serializers.ValidationError({"non_field_errors": ["Tutor profili topilmadi."]})
            tutor.status = True
            tutor.save()

        else:
            raise serializers.ValidationError({
                "non_field_errors": ["Noma'lum role."]
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