# models.py yoki signals.py faylida
import os
from django.db import models
from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver
from .models import SystemSettings, Banner

@receiver(pre_save, sender=SystemSettings)
def auto_delete_system_file_on_change(sender, instance, **kwargs):
    """
    SystemSettings yangilanganda eski fayllarni o'chiradi
    """
    if not instance.pk:
        return False
    
    try:
        old_instance = SystemSettings.objects.get(pk=instance.pk)
        
        # shartnoma_uz tekshirish
        old_file_uz = old_instance.shartnoma_uz
        new_file_uz = instance.shartnoma_uz
        if old_file_uz and old_file_uz != new_file_uz:
            if os.path.isfile(old_file_uz.path):
                os.remove(old_file_uz.path)
        
        # shartnoma_ru tekshirish
        old_file_ru = old_instance.shartnoma_ru
        new_file_ru = instance.shartnoma_ru
        if old_file_ru and old_file_ru != new_file_ru:
            if os.path.isfile(old_file_ru.path):
                os.remove(old_file_ru.path)
                
    except SystemSettings.DoesNotExist:
        pass
    except Exception as e:
        print(f"SystemSettings fayl o'chirishda xatolik: {e}")

@receiver(post_delete, sender=SystemSettings)
def auto_delete_system_file_on_delete(sender, instance, **kwargs):
    """
    SystemSettings o'chirilganda fayllarni o'chiradi
    """
    # shartnoma_uz o'chirish
    if instance.shartnoma_uz:
        if os.path.isfile(instance.shartnoma_uz.path):
            os.remove(instance.shartnoma_uz.path)
    
    # shartnoma_ru o'chirish
    if instance.shartnoma_ru:
        if os.path.isfile(instance.shartnoma_ru.path):
            os.remove(instance.shartnoma_ru.path)

# Banner uchun signal handlerlar
@receiver(pre_save, sender=Banner)
def auto_delete_banner_image_on_change(sender, instance, **kwargs):
    """
    Banner yangilanganda eski rasmni o'chiradi
    """
    if not instance.pk:
        return False
    
    try:
        old_instance = Banner.objects.get(pk=instance.pk)
        old_image = old_instance.image
        new_image = instance.image
        
        if old_image and old_image != new_image:
            if os.path.isfile(old_image.path):
                os.remove(old_image.path)
                
    except Banner.DoesNotExist:
        pass
    except Exception as e:
        print(f"Banner rasm o'chirishda xatolik: {e}")

@receiver(post_delete, sender=Banner)
def auto_delete_banner_image_on_delete(sender, instance, **kwargs):
    """
    Banner o'chirilganda rasmni o'chiradi
    """
    if instance.image:
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)