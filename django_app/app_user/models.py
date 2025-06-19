from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from datetime import timedelta
from django.utils.timezone import now















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


class Class(models.Model):
    name = models.CharField(max_length=20, unique=True, verbose_name="Sinf nomi")  # Masalan, "5", "6", "7"

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Sinf"
        verbose_name_plural = "Sinflar"
class Subject_Category(models.Model):
    name  = models.CharField(max_length=200, verbose_name="Fan bo'limi")

    def __str__(self):
        return self.name
    class Meta:
        verbose_name = "Fan Bo'limi"
        verbose_name_plural = "Fan Bo'limi"


class Subject(models.Model):
    name = models.CharField(max_length=200, verbose_name="Fan nomi")
    image_uz = models.ImageField(upload_to="FILES/SubjectUZ", blank=True, null=True)
    image_ru = models.ImageField(upload_to="FILES/SubjectRU", blank=True, null=True)
    teachers = models.ManyToManyField(Teacher, related_name="subjects", verbose_name="O‘qituvchilar")
    classes = models.ForeignKey(Class, on_delete=models.SET_NULL, related_name="subjects", verbose_name="Sinf", null=True)
    category = models.ForeignKey(Subject_Category, on_delete=models.SET_NULL, related_name="subjects", verbose_name="Fan bo'limi", null=True)
    
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib raqami")  # ✅ Qo‘shildi

    def __str__(self):
        return f"{self.name} - {self.classes.name}"

    class Meta:
        verbose_name = "Fan"
        verbose_name_plural = "Fanlar"
        ordering = ['order']  # ✅ Tartibli chiqadi
from django.utils.timezone import now

def generate_daily_user_id():
    today = now().strftime("%Y%m%d")  # Masalan: '20250507'
    today_users = Student.objects.filter(student_date__date=now().date()).count() + 1
    return f"{today}{today_users:04d}"  # Masalan: '202505070001'
class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile', verbose_name="Foydalanuvchi")
    identification  = models.CharField(max_length=20, unique=True, default=generate_daily_user_id)
    full_name = models.CharField(max_length=200, verbose_name="To‘liq ism")
    region = models.CharField(max_length=200, verbose_name="Viloyat")
    districts = models.CharField(max_length=200, verbose_name="Tuman")
    address = models.CharField(max_length=500, verbose_name="Manzil")
    brithday = models.CharField(max_length=20, verbose_name="Tug‘ilgan kun")
    academy_or_school = models.CharField(max_length=200, verbose_name="Akademiya yoki maktab")
    academy_or_school_name = models.CharField(max_length=500, verbose_name="Muassasa nomi")
    class_name = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True)
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



class StudentSubjectAccess(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='subject_access')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=False)
    access_start = models.DateTimeField(null=True, blank=True)
    access_end = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.student.full_name} - {self.subject.name} ({'ochiq' if self.is_active else 'yopiq'})"

    class Meta:
        verbose_name = "Fan kirish huquqi"
        verbose_name_plural = "Fan kirish huquqlari"
        unique_together = ('student', 'subject')



class Referral(models.Model):
    referrer = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='referrals_made', verbose_name="Taklif qilgan")
    referred = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='referral_info', verbose_name="Taklif qilingan")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqti")

    def __str__(self):
        return f"{self.referrer.full_name} -> {self.referred.full_name}"

    class Meta:
        verbose_name = "Referal"
        verbose_name_plural = "Referallar"