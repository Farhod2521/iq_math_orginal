from rest_framework import serializers
from .models import User, Student, UserSMSAttempt, Class, Teacher
from django.core.cache import cache
import random
from .sms_service import send_sms, send_verification_email, send_login_parol_email# SMS sending function
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from django.utils.timezone import now
User = get_user_model()




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
    region = serializers.CharField(required=True)
    districts = serializers.CharField(required=True)
    address = serializers.CharField(required=True)
    brithday = serializers.CharField(required=True)
    document_type = serializers.CharField(required=True)
    document = serializers.CharField(required=True)


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
        classes = validated_data.pop('classes')  # ManyToManyField ni olish

        teacher_data = {
            "full_name": validated_data.pop("full_name"),
            "address": validated_data.pop("address"),
            "brithday": validated_data.pop("brithday"),
            "region": validated_data.pop("region"),
            "districts": validated_data.pop("districts"),
            "document_type": validated_data.pop("document_type"),
            "document": validated_data.pop("document"),
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
        teacher.classes.set(classes)  # ManyToManyField ga sinflarni bog'lash

        # SMS yuborish
        send_sms(phone, sms_code)

        return user



##############################################################
###################     STUNDENT    REGISTER   ###############
##############################################################
class StudentRegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    phone = serializers.CharField(required=True)
    region = serializers.CharField(required=True)
    districts = serializers.CharField(required=True)
    address = serializers.CharField(required=True)
    brithday = serializers.CharField(required=True)
    academy_or_school = serializers.CharField(required=True)
    academy_or_school_name = serializers.CharField(required=True)
    class_name = serializers.SlugRelatedField(
    queryset=Class.objects.all(),
    slug_field='name', 
    required=True
    )
    document_type = serializers.CharField(required=True)
    type_of_education = serializers.CharField(required=True)
    document = serializers.CharField(required=True)

    def validate_user_data(self, email, phone):
        """Foydalanuvchi ma'lumotlarini tekshirish"""
        user = User.objects.filter(phone=phone).first()
        if user:
            student = getattr(user, "student_profile", None)
            if student and not student.status:
                # 5 daqiqa ichida qayta urinishni tekshirish
                time_diff = now() - student.student_date
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
        
        if Student.objects.filter(document=attrs.get("document")).exists():
            raise serializers.ValidationError("Bu shaxs allaqachon ro'yxatdan o'tgan.")

        return attrs

    def create(self, validated_data):
        phone = validated_data['phone']
        email = validated_data['email']
        class_name = validated_data.pop('class_name')  # `PrimaryKeyRelatedField` ni olish

        student_data = {
            'full_name': validated_data.pop('full_name'),
            'address': validated_data.pop('address'),
            'brithday': validated_data.pop('brithday'),
            'academy_or_school': validated_data.pop('academy_or_school'),
            'academy_or_school_name': validated_data.pop('academy_or_school_name'),
            'class_name': class_name,  # ForeignKey sifatida berish
            "region": validated_data.pop('region'),
            "districts": validated_data.pop('districts'),
            "document_type": validated_data.pop('document_type'),
            "document": validated_data.pop('document'),
            "type_of_education": validated_data.pop('type_of_education'),
            "status": False,
            "student_date": now()
        }

        # Yangi foydalanuvchi yaratish
        user = User.objects.create(phone=phone, email=email, role='student')

        # SMS kod yaratish
        sms_code = str(random.randint(10000, 99999))
        user.sms_code = sms_code
        user.set_unusable_password()
        user.save()

        # Student ma'lumotlarini saqlash
        student_data['user'] = user
        Student.objects.create(**student_data)

        # SMS yuborish
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
            student = Student.objects.get(user=user)
            student.status = True
            student.save()
        except Student.DoesNotExist:
            raise serializers.ValidationError({
                "non_field_errors": ["Student profili topilmadi."]
            })

        return {"phone": phone, "password": password, "user": user}