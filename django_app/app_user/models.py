from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from datetime import timedelta
from django.utils.timezone import now
from django_app.app_teacher.models import Subject


class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("Telefon raqami kiritilishi shart")
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser uchun `is_staff=True` bo‘lishi kerak.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser uchun `is_superuser=True` bo‘lishi kerak.')

        return self.create_user(phone, password, **extra_fields)


class User(AbstractUser):
    username = None  # username maydonini o‘chirish
    phone = models.CharField(max_length=15, unique=True, verbose_name="Telefon raqam")
    role = models.CharField(
        max_length=10,
        choices=[('student', 'Student'), ('teacher', 'Teacher'), ('admin', 'Admin')],
        default='student',
        verbose_name="Foydalanuvchi roli"
    )
    sms_code = models.CharField(max_length=6, blank=True, null=True, verbose_name="SMS kod")

    USERNAME_FIELD = 'phone' 
    REQUIRED_FIELDS = []  
    objects = UserManager()  

    def __str__(self):
        return f'{self.phone} - {self.role}'

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"


class Class(models.Model):
    name = models.CharField(max_length=20, unique=True, verbose_name="Sinf nomi")  # Masalan, "5", "6", "7"

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Sinf"
        verbose_name_plural = "Sinflar"


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile', verbose_name="Foydalanuvchi")
    full_name = models.CharField(max_length=200, verbose_name="To‘liq ism")
    region = models.CharField(max_length=200, verbose_name="Viloyat")
    districts = models.CharField(max_length=200, verbose_name="Tuman")
    address = models.CharField(max_length=500, verbose_name="Manzil")
    brithday = models.CharField(max_length=20, verbose_name="Tug‘ilgan kun")
    academy_or_school = models.CharField(max_length=200, verbose_name="Akademiya yoki maktab")
    academy_or_school_name = models.CharField(max_length=500, verbose_name="Muassasa nomi")
    class_name = models.ForeignKey(Class, on_delete=models.SET_NULL, null=True, related_name='students', verbose_name="Sinf")
    document_type = models.CharField(max_length=50, verbose_name="Hujjat turi")
    document = models.CharField(max_length=20, verbose_name="Hujjat raqami")
    type_of_education = models.CharField(max_length=200, verbose_name="Ta’lim turi")
    status = models.BooleanField(default=False, verbose_name="Holat")
    student_date = models.DateTimeField(auto_now=True, null=True, verbose_name="Ro‘yxatdan o‘tgan sana")

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = "O‘quvchi"
        verbose_name_plural = "O‘quvchilar"


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile', verbose_name="Foydalanuvchi") 
    full_name = models.CharField(max_length=200, verbose_name="To‘liq ism")
    region = models.CharField(max_length=200, verbose_name="Viloyat")
    districts = models.CharField(max_length=200, verbose_name="Tuman")
    address = models.CharField(max_length=500, verbose_name="Manzil")
    brithday = models.CharField(max_length=20, verbose_name="Tug‘ilgan kun")
    document_type = models.CharField(max_length=50, verbose_name="Hujjat turi")
    document = models.CharField(max_length=20, verbose_name="Hujjat raqami")
    status = models.BooleanField(default=False, verbose_name="Holat")
    is_verified_teacher = models.BooleanField(default=False, verbose_name="O‘qituvchi")
    teacher_date = models.DateTimeField(auto_now=True, null=True, verbose_name="Ro‘yxatdan o‘tgan sana")

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = "O‘qituvchi"
        verbose_name_plural = "O‘qituvchilar"


class UserSMSAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sms_attempts')
    created_at = models.DateTimeField(auto_now_add=True)
    wrong_attempts = models.IntegerField(default=0)

    @staticmethod
    def can_send_sms(user):
        """
        Ushbu metod foydalanuvchi yana SMS kod olishi mumkinligini tekshiradi.
        Agar SMS olish uchun kutish vaqti bo‘lsa, qolgan kutish vaqtini qaytaradi.
        """
        attempts = UserSMSAttempt.objects.filter(user=user).order_by('created_at')

        if attempts.count() < 3:
            return True, None  # Dastlabki 3 ta SMS cheklovsiz ketadi
        
        last_attempt = attempts.last()
        attempt_count = attempts.count()

        if attempt_count == 3:
            wait_time = 5 * 60  # 5 daqiqa
        elif attempt_count == 4:
            wait_time = 30 * 60  # 30 daqiqa
        else:
            wait_time = (2 ** (attempt_count - 3)) * 60  # Har safar 2 baravar ortadi

        # Agar kutish vaqti o‘tmagan bo‘lsa
        if now() - last_attempt.created_at < timedelta(seconds=wait_time):
            remaining_time = timedelta(seconds=wait_time) - (now() - last_attempt.created_at)
            return False, remaining_time

        return True, None

    @staticmethod
    def register_attempt(user, wrong=False):
        """
        Foydalanuvchiga SMS yuborishdan oldin ushbu metod orqali urinishni ro‘yxatga olish.
        wrong=True bo‘lsa, urinish noto‘g‘ri kiritilgan hisoblanadi.
        """
        attempt = UserSMSAttempt.objects.create(user=user)
        if wrong:
            attempt.wrong_attempts += 1
            attempt.save()

