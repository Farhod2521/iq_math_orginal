from rest_framework import serializers
from .models import User, Student, UserSMSAttempt, Class, Teacher, Subject, Referral, Parent, Tutor, StudentLoginHistory
from django.core.cache import cache
import random
from .sms_service import send_sms, send_verification_email, send_login_parol_email# SMS sending function
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from django.utils.timezone import now
from django_app.app_payments.models import Subscription, SubscriptionSetting, Payment
from django_app.app_student.models import  StudentReferralTransaction
from django_app.app_tutor.models import TutorReferralTransaction
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

    def validate(self, attrs):
        phone = attrs.get("phone")
        role = attrs.get("role")

        user = User.objects.filter(phone=phone).first()
        if user:
            # userning haqiqiy roli
            existing_role = user.role

            # student status check
            if hasattr(user, 'student_profile'):
                if user.student_profile.status:
                    raise serializers.ValidationError("Bu telefon raqam allaqachon ro'yxatdan o'tgan.")
                if existing_role != role:
                    raise serializers.ValidationError(
                        f"Siz faqat '{existing_role}' roli orqali ro'yxatdan o'tishingiz mumkin."
                    )

            # parent status check
            elif hasattr(user, 'parent_profile'):
                if user.parent_profile.status:
                    raise serializers.ValidationError("Bu telefon raqam allaqachon ro'yxatdan o'tgan.")
                if existing_role != role:
                    raise serializers.ValidationError(
                        f"Siz faqat '{existing_role}' roli orqali ro'yxatdan o'tishingiz mumkin."
                    )

            # tutor status check
            elif hasattr(user, 'tutor_profile'):
                if user.tutor_profile.status:
                    raise serializers.ValidationError("Bu telefon raqam allaqachon ro'yxatdan o'tgan.")
                if existing_role != role:
                    raise serializers.ValidationError(
                        f"Siz faqat '{existing_role}' roli orqali ro'yxatdan o'tishingiz mumkin."
                    )

        # student bo'lsa class_name majburiy
        if role == "student" and not attrs.get("class_name"):
            raise serializers.ValidationError({"class_name": "Student uchun sinf tanlash shart."})

        return attrs

    def create(self, validated_data):
        phone = validated_data['phone']
        role = validated_data['role']
        full_name = validated_data['full_name']
        lang = validated_data['lang', None]
        class_name = validated_data.pop('class_name', None)
        referral_code = validated_data.pop('referral_code', None)

        sms_code = str(random.randint(10000, 99999))

        # 1. Mavjud userni tekshirish
        user = User.objects.filter(phone=phone).first()

        if user:
            # Agar mavjud bo‘lsa va hali tasdiqlanmagan bo‘lsa — sms_code yangilanadi
            if hasattr(user, 'student_profile') and not user.student_profile.status:
                user.sms_code = sms_code
                user.save(update_fields=['sms_code'])
                send_sms(phone, sms_code)
                return user

            if hasattr(user, 'parent_profile') and not user.parent_profile.status:
                user.sms_code = sms_code
                user.save(update_fields=['sms_code'])
                send_sms(phone, sms_code)
                return user

            if hasattr(user, 'tutor_profile') and not user.tutor_profile.status:
                user.sms_code = sms_code
                user.save(update_fields=['sms_code'])
                send_sms(phone, sms_code)
                return user

        # 2. Yangi foydalanuvchi yaratish
        user = User.objects.create(phone=phone, role=role)
        user.sms_code = sms_code
        user.set_unusable_password()
        user.save()

        # 3. Role bo‘yicha profil yaratish
        if role == "student":
            student = Student.objects.create(
                user=user,
                full_name=full_name,
                class_name=class_name,
                lang=lang,
                status=False,
                student_date=now()
            )

            # 🎁 Trial obuna
            free_days = SubscriptionSetting.objects.first().free_trial_days
            Subscription.objects.create(
                student=student,
                start_date=now(),
                end_date=now() + timedelta(days=free_days),
                is_paid=False
            )

            # 🧩 REFERAL LOGIKA
            if referral_code:
                referral_code = referral_code.strip()

                # Tutor referali (T bilan boshlansa)
                if referral_code.startswith('T'):
                    try:
                        ref_tutor = Tutor.objects.get(identification=referral_code)
                        TutorReferralTransaction.objects.create(
                            student=student,
                            tutor=ref_tutor,
                            payment_amount=0,
                            bonus_amount=0
                        )
                    except Tutor.DoesNotExist:
                        pass

                # Student referali (faqat raqam)
                elif referral_code.isdigit():
                    try:
                        ref_student = Student.objects.get(identification=referral_code)
                        StudentReferralTransaction.objects.create(
                            student=student,
                            by_student=ref_student,
                            payment_amount=0,
                            bonus_amount=0
                        )
                    except Student.DoesNotExist:
                        pass

        elif role == "parent":
            Parent.objects.create(
                user=user,
                full_name=full_name,
                status=False
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
from rest_framework import serializers
from datetime import datetime
import pytz
class StudentSerializer(serializers.ModelSerializer):
    class_num = serializers.SerializerMethodField()
    subject_name_uz = serializers.SerializerMethodField()
    subject_name_ru = serializers.SerializerMethodField()
    registration_date = serializers.SerializerMethodField()
    registration_time = serializers.SerializerMethodField()
    last_login_time = serializers.SerializerMethodField()
    last_payment_amount = serializers.SerializerMethodField()
    subscription_end_date = serializers.SerializerMethodField()
    remaining_days = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            "id", "full_name", "identification", "region", "districts", "address", "brithday",
            "academy_or_school", "academy_or_school_name", "class_num",
            "subject_name_uz", "subject_name_ru", "document_type", "document",
            "type_of_education", "status", "registration_date", "registration_time",
            "last_login_time", "last_payment_amount", "subscription_end_date",
            "remaining_days",
        ]

    def get_class_num(self, obj):
        return obj.class_name.classes.name if obj.class_name else None

    def get_subject_name_uz(self, obj):
        return obj.class_name.name_uz if obj.class_name else None

    def get_subject_name_ru(self, obj):
        return obj.class_name.name_ru if obj.class_name else None

    def get_registration_date(self, obj):
        if obj.student_date:
            return obj.student_date.astimezone(pytz.timezone("Asia/Ashgabat")).strftime('%d/%m/%Y')
        return None

    def get_registration_time(self, obj):
        if obj.student_date:
            return obj.student_date.astimezone(pytz.timezone("Asia/Ashgabat")).strftime('%H:%M:%S')
        return None

    def get_last_login_time(self, obj):
        last_login_obj = StudentLoginHistory.objects.filter(student=obj).order_by('-login_time').first()
        if last_login_obj:
            return last_login_obj.login_time.astimezone(pytz.timezone("Asia/Ashgabat")).strftime('%d/%m/%Y %H:%M')
        return None

    def get_last_payment_amount(self, obj):
        last_payment = Payment.objects.filter(student=obj, status="success").order_by('-payment_date').first()
        return float(last_payment.amount) if last_payment else 0

    def get_subscription_end_date(self, obj):
        subscription = getattr(obj, 'subscription', None)
        if subscription and subscription.end_date:
            return subscription.end_date.strftime('%d/%m/%Y')
        return None

    def get_remaining_days(self, obj):
        subscription = getattr(obj, 'subscription', None)
        if subscription and subscription.end_date:
            today = datetime.now(pytz.timezone("Asia/Ashgabat")).date()
            diff_days = (subscription.end_date.date() - today).days
            return diff_days if diff_days > 0 else 0
        return None



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