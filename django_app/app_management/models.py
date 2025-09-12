from django.db import models
from ckeditor.fields import RichTextField
# Create your models here.
from django.db import models
import uuid
from django.utils import timezone
from datetime import timedelta

from django_app.app_user.models import  Student, Teacher, Tutor
class SystemSettings(models.Model):
    logo = models.ImageField(upload_to='system/logo/', blank=True, null=True, verbose_name="Logo")
    about =  RichTextField(verbose_name="Biz Haqimizda")
    instagram_link = models.URLField(blank=True, null=True, verbose_name="Instagram Linki")
    telegram_link = models.URLField(blank=True, null=True, verbose_name="Telegram Linki")
    youtube_link = models.URLField(blank=True, null=True, verbose_name="YouTube Linki")
    twitter_link = models.URLField(blank=True, null=True, verbose_name="Twitter Linki")
    facebook_link = models.URLField(blank=True, null=True, verbose_name="Facebook Linki")
    linkedin_link = models.URLField(blank=True, null=True, verbose_name="LinkedIn Linki")

    shartnoma_uz = models.FileField(upload_to='system/docs/uz/', blank=True, null=True, verbose_name="shartnoma (O'zbekcha)")
    shartnoma_ru = models.FileField(upload_to='system/docs/ru/', blank=True, null=True, verbose_name="shartnoma (Ruscha)")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="So'nggi yangilanish vaqti")

    def __str__(self):
        return "Tizim Sozlamalari"

    class Meta:
        verbose_name = "Tizim Sozlamasi"
        verbose_name_plural = "Tizim Sozlamalari"

class  Banner(models.Model):
    image  =  models.ImageField(upload_to="Media/BANNER/")
    desc =  models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        verbose_name = "Banner"
        verbose_name_plural = "Banner"

class FAQ(models.Model):
    question = models.CharField(max_length=500, verbose_name="Savol")
    answer = RichTextField(verbose_name="Javob")

    class Meta:
        verbose_name = "TSS"  # "Tez-tez so'raladigan savollar"
        verbose_name_plural = "Tez-tez so‘raladigan savollar"
        ordering = ["id"]

    def __str__(self):
        return self.question  
    


class ReferralAndCouponSettings(models.Model):
    teacher_referral_bonus_points = models.PositiveIntegerField(
        default=0,
        verbose_name="O‘qituvchi uchun referal ball"
    )
    student_referral_bonus_points = models.PositiveIntegerField(
        default=0,
        verbose_name="O‘quvchi uchun referal ball"
    )
    coupon_discount_percent = models.PositiveIntegerField(
        default=0,
        help_text="Kupon kodi orqali beriladigan chegirma foizi",
        verbose_name="Kupon chegirma foizi"
    )
    coupon_valid_days = models.PositiveIntegerField(
        default=30,
        help_text="Kupon kodi amal qilish muddati (kunlarda)",
        verbose_name="Kupon amal qilish muddati (kun)"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqti"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Yangilangan vaqti"
    )

    def __str__(self):
        return f"Sozlamalar (yangilangan: {self.updated_at.date()})"

    class Meta:
        verbose_name = "Referal va kupon sozlamasi"
        verbose_name_plural = "Referal va kupon sozlamalari"

class SystemCoupon(models.Model):
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Kupon kodi"
    )
    discount_percent = models.PositiveIntegerField(
        verbose_name="Chegirma foizi (%)"
    )
    valid_until = models.DateTimeField(
        verbose_name="Amal qilish muddati"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Faolligi"
    )

    class Meta:
        verbose_name = "Tizim kuponi"
        verbose_name_plural = "Tizim kuponlari"

    def __str__(self):
        return f"{self.code} ({self.discount_percent}%)"

class Product(models.Model):
    name = models.CharField(max_length=255, verbose_name="Mahsulot nomi")
    image = models.ImageField(upload_to='products/', verbose_name="Mahsulot rasmi")
    coin = models.PositiveIntegerField(verbose_name="Kerakli tanga")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Mahsulot"
        verbose_name_plural = "Mahsulotlar"


class ConversionRate(models.Model):
    coin_to_score = models.PositiveIntegerField(
        verbose_name="1 tangaga teng ball miqdori", default=1
    )
    coin_to_money = models.DecimalField(
        max_digits=10, decimal_places=3, verbose_name="1 tangaga teng pul miqdori"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Konversiya kursi"
        verbose_name_plural = "Konversiya kurslari"

    def __str__(self):
        return f"1 coin = {self.coin_to_score} ball = {self.coin_to_money} so‘m"


class Coupon(models.Model):
    code = models.CharField(max_length=20, unique=True)
    discount_percent = models.PositiveIntegerField(default=10, verbose_name="Chegirma foizi")
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField()
    created_by_student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True)
    created_by_tutor = models.ForeignKey(Tutor, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True, verbose_name="Faolmi")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_valid(self):
        now = timezone.now()
        return self.is_active and self.valid_from <= now <= self.valid_until

    def __str__(self):
        return self.code

    class Meta:
        verbose_name = "Kupon"
        verbose_name_plural = "Kuponlar"


class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    used_by_student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True)
    used_by_tutor = models.ForeignKey(Tutor, on_delete=models.SET_NULL, null=True, blank=True)
    used_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.coupon.code} used on {self.used_at.date()}"

    class Meta:
        verbose_name = "Kupon ishlatilishi"
        verbose_name_plural = "Kupon ishlatilishlari"
        unique_together = ('coupon', 'used_by_student', 'used_by_tutor')




class Coupon_Tutor_Student(models.Model):
    code = models.CharField(max_length=20, unique=True)
    discount_percent = models.PositiveIntegerField(default=10, verbose_name="Chegirma foizi")
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField()
    created_by_student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True)
    created_by_tutor = models.ForeignKey(Tutor, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True, verbose_name="Faolmi")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_valid(self):
        now = timezone.now()
        return self.is_active and self.valid_from <= now <= self.valid_until

    def __str__(self):
        return self.code

    class Meta:
        verbose_name = "Kupon"
        verbose_name_plural = "Kuponlar"


class CouponUsage_Tutor_Student(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    used_by_student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True)
    used_by_tutor = models.ForeignKey(Tutor, on_delete=models.SET_NULL, null=True, blank=True)
    used_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.coupon.code} used on {self.used_at.date()}"

    class Meta:
        verbose_name = "Kupon ishlatilishi"
        verbose_name_plural = "Kupon ishlatilishlari"