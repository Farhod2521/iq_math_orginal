from django.db import models
from ckeditor.fields import RichTextField
# Create your models here.
from django.db import models

class SystemSettings(models.Model):
    logo = models.ImageField(upload_to='system/logo/', blank=True, null=True, verbose_name="Logo")

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
    referral_bonus_points = models.PositiveIntegerField(default=0, help_text="Referal orqali foydalanuvchi taklif qilganda beriladigan ball miqdori")
    coupon_discount_percent = models.PositiveIntegerField(default=0, help_text="Kupon kodi orqali beriladigan chegirma foizi")
    coupon_valid_days = models.PositiveIntegerField(default=30, help_text="Kupon kodi amal qilish muddati (kunlarda)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"SystemSettings (updated: {self.updated_at.date()})"


class Product(models.Model):
    name = models.CharField(max_length=255, verbose_name="Mahsulot nomi")
    image = models.ImageField(upload_to='products/', verbose_name="Mahsulot rasmi")
    coin = models.PositiveIntegerField(verbose_name="Kerakli tanga")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Mahsulot"
        verbose_name_plural = "Mahsulotlar"