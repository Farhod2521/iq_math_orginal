from django.db import models
from ckeditor.fields import RichTextField
# Create your models here.
from django.db import models
import uuid
from django.utils import timezone
from datetime import timedelta
import os
from django_app.app_user.models import  Student, Teacher, Tutor




class AndroidVersion(models.Model):
    android_latest_version = models.CharField(
        max_length=200, verbose_name="Android version"
    )
    android_force_update = models.BooleanField(default=False)

    ios_latest_version = models.CharField(
        max_length=200, verbose_name="iOS version"
    )
    ios_force_update = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "Mobile App Versions"
    

class UploadSetting(models.Model):
    max_size_mb = models.PositiveIntegerField(
        default=5,
        verbose_name="Maksimal fayl hajmi (MB)",
        help_text="Yuklanadigan faylning ruxsat etilgan maksimal hajmi (megabayt)"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="So‘nggi yangilangan vaqti"
    )

    class Meta:
        verbose_name = "Yuklash hajmi sozlamasi"
        verbose_name_plural = "Yuklash hajmi sozlamalari"

    def __str__(self):
        return f"{self.max_size_mb} MB"

    @property
    def max_size_bytes(self) -> int:
        """Maksimal hajm (baytlarda)"""
        return self.max_size_mb * 1024 * 1024




class UploadedFile(models.Model):
    file = models.FileField(upload_to="uploaded_files/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Yuklangan fayl"
        verbose_name_plural = "Yuklangan fayllar"

    def __str__(self):
        return self.file.name
    def delete(self, *args, **kwargs):
        # Faylni filesystemdan ham o'chiramiz
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        super().delete(*args, **kwargs)

class Category(models.Model):
    title = models.CharField(max_length=200, verbose_name="Kategoriya nomi")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"
        ordering = ['title']


class Tag(models.Model):
    title = models.CharField(max_length=200, verbose_name="Teg nomi")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Teg"
        verbose_name_plural = "Teglar"
        ordering = ['title']


class Elon(models.Model):
    title = models.CharField(max_length=255, verbose_name="Sarlavha")
    text = RichTextField(verbose_name="Matn (boy matn)")
    image = models.ImageField(upload_to='elon_images/', null=True, blank=True, verbose_name="Rasm")

    categories = models.ManyToManyField(Category, blank=True, related_name="elons", verbose_name="Kategoriyalar")
    tags = models.ManyToManyField(Tag, blank=True, related_name="elons", verbose_name="Teglar")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana")
    notification_status =  models.BooleanField(default=False, verbose_name="Xabarnoma")
    news_status =  models.BooleanField(default=False,  verbose_name="Yanglik")
    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "E'lon"
        verbose_name_plural = "E'lonlar"
        ordering = ['-created_at']

class Motivation(models.Model):
    title = models.CharField(
        max_length=255,
        verbose_name="Sarlavha"
    )
    content = RichTextField(
        verbose_name="Matn (motivatsion so‘zlar)"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Faolmi?"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan sana"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Yangilangan sana"
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Motivatsion matn"
        verbose_name_plural = "Motivatsion matnlar"
        ordering = ["-created_at"]

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
    url =  models.CharField(max_length=1000, null=True, blank=True, verbose_name="Youtube video link")
    class Meta:
        verbose_name = "TSS"  # "Tez-tez so'raladigan savollar"
        verbose_name_plural = "Tez-tez so‘raladigan savollar"
        ordering = ["id"]

    def __str__(self):
        return self.question  
    


class ReferralAndCouponSettings(models.Model):
    teacher_referral_bonus_points = models.PositiveIntegerField(
        default=0,
        verbose_name="O‘qituvchi uchun referal foizi"
    )
    student_referral_bonus_points = models.PositiveIntegerField(
        default=0,
        verbose_name="O‘quvchi uchun referal foizi"
    )
    coupon_discount_percent = models.PositiveIntegerField(
        default=0,
        help_text="Kupon kodi orqali beriladigan chegirma foizi Student va O'qtuvchilar uchun",
        verbose_name="Student va O'qtuvchilar kupon chegirma foizi"
    )
    coupon_discount_percent_teacher = models.PositiveIntegerField(
        default=0,
        help_text="Kupon kodi orqali beriladigan chegirma foizi Mentor uchun ",
        verbose_name="Mentor kupon chegirma foizi"
    )
    coupon_valid_days = models.PositiveIntegerField(
        default=30,
        help_text="Kupon kodi amal qilish muddati (kunlarda)",
        verbose_name="Kupon amal qilish muddati (kun)"
    )
    referral_valid_days = models.PositiveIntegerField(
        default=30,
        help_text="Referral kodi amal qilish muddati (kunlarda)",
        verbose_name="Referral amal qilish muddati (kun)"
    )
    coupon_student_cashback_percent = models.PositiveIntegerField(
        default=0,
        help_text="Kupon ishlatilganda studentga beriladigan keshbek foizi",
        verbose_name="Student keshbek (%)"
    )
    coupon_teacher_cashback_percent = models.PositiveIntegerField(
        default=0,
        help_text="Kupon ishlatilganda teacherga beriladigan keshbek foizi",
        verbose_name="Teacher keshbek (%)"
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


class Product(models.Model):
    name = models.CharField(max_length=255, verbose_name="Mahsulot nomi")
    image = models.ImageField(upload_to='products/', verbose_name="Mahsulot rasmi")
    count =  models.PositiveIntegerField(verbose_name="Mahsulot soni", default=0)
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


# class CouponUsage(models.Model):
#     coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
#     used_by_student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True)
#     used_by_tutor = models.ForeignKey(Tutor, on_delete=models.SET_NULL, null=True, blank=True)
#     used_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.coupon.code} used on {self.used_at.date()}"

#     class Meta:
#         verbose_name = "Kupon ishlatilishi"
#         verbose_name_plural = "Kupon ishlatilishlari"
#         unique_together = ('coupon', 'used_by_student', 'used_by_tutor')




class Coupon_Tutor_Student(models.Model):
    code = models.CharField(max_length=20, unique=True)
    discount_percent = models.PositiveIntegerField(default=10, verbose_name="Chegirma foizi")
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField()

    created_by_student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True)
    created_by_tutor = models.ForeignKey(Tutor, on_delete=models.SET_NULL, null=True, blank=True)
    created_by_teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True)

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


class Referral_Tutor_Student(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="Referal kodi")
    bonus_percent = models.PositiveIntegerField(default=5, verbose_name="Bonus foizi")
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField()
    created_by_student = models.ForeignKey(
        Student,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Referalni yaratgan student"
    )
    created_by_tutor = models.ForeignKey(
        Tutor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Referalni yaratgan tutor"
    )
    is_active = models.BooleanField(default=True, verbose_name="Faolmi")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_valid(self):
        now = timezone.now()
        return self.is_active and self.valid_from <= now <= self.valid_until

    def __str__(self):
        return self.code

    class Meta:
        verbose_name = "Referal link"
        verbose_name_plural = "Referal linklar"


class CouponUsage_Tutor_Student(models.Model):
    coupon = models.ForeignKey(Coupon_Tutor_Student, on_delete=models.CASCADE, related_name='usages')
    used_by_student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True)
    used_by_tutor = models.ForeignKey(Tutor, on_delete=models.SET_NULL, null=True, blank=True)
    used_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.coupon.code} used on {self.used_at.date()}"

    class Meta:
        verbose_name = "Kupon ishlatilishi"
        verbose_name_plural = "Kupon ishlatilishlari"

    
class SolutionStatus(models.Model):
    subject_is_active = models.BooleanField(
        default=False,
        verbose_name="Fanlar bo‘yicha yechim tugmasi yoqilganmi?"
    )
    recommendation_is_active = models.BooleanField(
        default=False,
        verbose_name="Tavsiyalar bo‘yicha yechim tugmasi yoqilganmi?"
    )

    class Meta:
        verbose_name = "Yechim tugmalari holati"
        verbose_name_plural = "Yechim tugmalari holatlari"

    def __str__(self):
        return (
            f"Fanlar: {'Yoqilgan' if self.subject_is_active else 'O‘chirilgan'} | "
            f"Tavsiyalar: {'Yoqilgan' if self.recommendation_is_active else 'O‘chirilgan'}"
        )



from django.db import models


class Mathematician(models.Model):
    # Title — Olim FIO
    title = models.CharField(
        max_length=255,
        verbose_name="Olim FIO"
    )

    # Subtitle — qaysi fanlarga hissa qo‘shgan
    subtitle = models.CharField(
        max_length=500,
        verbose_name="Fanlarga qo‘shgan hissasi"
    )

    # Text — tug‘ilgan va vafot etgan yillari
    life_years = models.CharField(
        max_length=100,
        verbose_name="Tug‘ilgan va vafot etgan yillari"
    )

    # Rasm
    image = models.ImageField(
        upload_to="FILES/mathematicians/",
        verbose_name="Rasm"
    )

    # Opisaniya — batafsil ma’lumot
    description = models.TextField(
        verbose_name="Batafsil ma'lumot"
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Faol"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan sana"
    )

    class Meta:
        verbose_name = "Matematik olim"
        verbose_name_plural = "Matematik olimlar"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
