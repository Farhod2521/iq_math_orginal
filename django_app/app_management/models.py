from django.db import models

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
