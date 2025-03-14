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
    phone = models.CharField(max_length=15, unique=True)
    role = models.CharField(
        max_length=10,
        choices=[('student', 'Student'), ('teacher', 'Teacher'), ('admin', 'Admin')],
        default='student'
    )
    sms_code = models.CharField(max_length=6, blank=True, null=True)

    USERNAME_FIELD = 'phone' 
    REQUIRED_FIELDS = []  

    objects = UserManager()  

    def __str__(self):
        return f'{self.phone} - {self.role}'

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    full_name = models.CharField(max_length=200)
    region = models.CharField(max_length=200)
    districts = models.CharField(max_length=200)
    address = models.CharField(max_length=500)
    brithday = models.CharField(max_length=20)
    academy_or_school = models.CharField(max_length=200)
    academy_or_school_name = models.CharField(max_length=500)
    class_name = models.CharField(max_length=20)
    document_type  = models.CharField(max_length=50)
    document  =  models.CharField(max_length=20)
    type_of_education =  models.CharField(max_length=200)
    status = models.BooleanField(default=False)
    student_date = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return self.full_name
    

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    full_name = models.CharField(max_length=200)
    region = models.CharField(max_length=200)
    districts = models.CharField(max_length=200)
    address = models.CharField(max_length=500)
    brithday = models.CharField(max_length=20)
    document_type  = models.CharField(max_length=50)
    document  =  models.CharField(max_length=20)
    status = models.BooleanField(default=False)
    teacher_date = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return self.full_name