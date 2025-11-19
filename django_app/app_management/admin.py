from django.contrib import admin
from .models import  (
    Motivation, SystemSettings, FAQ, Product, ReferralAndCouponSettings, 
    Banner, Coupon_Tutor_Student, SystemCoupon,ConversionRate, SolutionStatus,
    Elon, Category, Tag, UploadedFile
    )
from modeltranslation.admin import TranslationAdmin
from django.utils.html import format_html
import os



@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ("id", "file", "uploaded_at")
    search_fields = ("file",)
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "title")
    search_fields = ("title",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "title")
    search_fields = ("title",)


@admin.register(Elon)
class ElonAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "created_at", "updated_at")
    search_fields = ("title", "text")
    list_filter = ("created_at", "categories", "tags")
    filter_horizontal = ("categories", "tags")
    readonly_fields = ("created_at", "updated_at")




@admin.register(Motivation)
class MotivationAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("title", "content")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Asosiy ma'lumotlar", {
            "fields": ("title", "content", "is_active")
        }),
        ("Vaqt ma'lumotlari", {
            "fields": ("created_at", "updated_at")
        }),
    )

    class Meta:
        verbose_name = "Motivatsion so‘z"
        verbose_name_plural = "Motivatsion so‘zlar"






@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'updated_at', 'shartnoma_uz_preview', 'shartnoma_ru_preview']
    readonly_fields = ['updated_at', 'shartnoma_uz_preview', 'shartnoma_ru_preview']
    fieldsets = (
        ("Logo", {
            'fields': ('logo',)
        }),
        ("Biz haqimizda", {
            'fields': ('about',)
        }),
        ("Ijtimoiy tarmoqlar", {
            'fields': (
                'instagram_link', 'telegram_link', 'youtube_link',
                'twitter_link', 'facebook_link', 'linkedin_link'
            )
        }),
        ("Shartnomalar", {
            'fields': ('shartnoma_uz', 'shartnoma_uz_preview', 'shartnoma_ru', 'shartnoma_ru_preview')
        }),
        ("Tizim holati", {
            'fields': ('updated_at',)
        }),
    )
    
    def shartnoma_uz_preview(self, obj):
        if obj.shartnoma_uz:
            return format_html(
                '<a href="{}" target="_blank">📄 Hozirgi faylni ko\'rish</a> | '
                '<a href="{}" download>📥 Yuklab olish</a>',
                obj.shartnoma_uz.url,
                obj.shartnoma_uz.url
            )
        return "Fayl yuklanmagan"
    shartnoma_uz_preview.short_description = "Shartnoma (O'Z) ko'rish"
    
    def shartnoma_ru_preview(self, obj):
        if obj.shartnoma_ru:
            return format_html(
                '<a href="{}" target="_blank">📄 Hozirgi faylni ko\'rish</a> | '
                '<a href="{}" download>📥 Yuklab olish</a>',
                obj.shartnoma_ru.url,
                obj.shartnoma_ru.url
            )
        return "Fayl yuklanmagan"
    shartnoma_ru_preview.short_description = "Shartnoma (RU) ko'rish"
    
    def save_model(self, request, obj, form, change):
        """
        Admin panelda saqlashda eski fayllarni o'chiradi
        """
        if change:
            # Eski instansiyani olish
            old_obj = SystemSettings.objects.get(pk=obj.pk)
            
            # Agar shartnoma_uz o'zgartirilgan bo'lsa
            if 'shartnoma_uz' in form.changed_data and old_obj.shartnoma_uz:
                if os.path.isfile(old_obj.shartnoma_uz.path):
                    os.remove(old_obj.shartnoma_uz.path)
            
            # Agar shartnoma_ru o'zgartirilgan bo'lsa
            if 'shartnoma_ru' in form.changed_data and old_obj.shartnoma_ru:
                if os.path.isfile(old_obj.shartnoma_ru.path):
                    os.remove(old_obj.shartnoma_ru.path)
        
        super().save_model(request, obj, form, change)
    
    def has_add_permission(self, request):
        """
        Faqat bitta SystemSettings obyekti bo'lishi uchun
        """
        count = SystemSettings.objects.count()
        if count >= 1:
            return False
        return True
    
    def has_delete_permission(self, request, obj=None):
        """
        SystemSettings ni o'chirishni taqiqlash
        """
        return False

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ['desc', 'image_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['desc']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 100px;" />',
                obj.image.url
            )
        return "Rasm yo'q"
    image_preview.short_description = "Rasm"
    
    def save_model(self, request, obj, form, change):
        """
        Banner yangilanganda eski rasmni o'chiradi
        """
        if change:
            old_obj = Banner.objects.get(pk=obj.pk)
            if 'image' in form.changed_data and old_obj.image:
                if os.path.isfile(old_obj.image.path):
                    os.remove(old_obj.image.path)
        
        super().save_model(request, obj, form, change)
    
    def get_readonly_fields(self, request, obj=None):
        """
        Yangi banner qo'shishda created_at ni ko'rsatmaslik
        """
        if obj:
            return ['created_at']
        return []

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question_uz']
    search_fields = ['question_uz', 'answer_uz', 'question_ru', 'answer_ru']

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields.pop('question', None)
        form.base_fields.pop('answer', None)  # optional: agar 'answer' ham kerak bo‘lmasa
        return form

@admin.register(ReferralAndCouponSettings)
class ReferralAndCouponSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'teacher_referral_bonus_points',
        'student_referral_bonus_points',
        'coupon_discount_percent',
        'coupon_valid_days',
        'coupon_student_cashback_percent',
        'coupon_teacher_cashback_percent',
        'created_at',
        'updated_at',
    )
@admin.register(SolutionStatus)
class SolutionStatusAdmin(admin.ModelAdmin):
    list_display = (
        'subject_is_active',
        'recommendation_is_active',
    )


@admin.register(Product)
class ProductAdmin(TranslationAdmin):  # model.ModelAdmin o'rniga TranslationAdmin ishlatiladi
    list_display = ['name_uz', 'name_ru', 'coin', 'get_price','count', 'image_tag']
    search_fields = ['name_uz', 'name_ru']
    readonly_fields = ['image_tag']

    def image_tag(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover;" />',
                obj.image.url
            )
        return "-"
    image_tag.short_description = 'Rasm'

    def get_price(self, obj):
        """Mahsulotning pul qiymatini chiqarish"""
        rate = ConversionRate.objects.last()
        if rate:
            return f"{obj.coin * rate.coin_to_money} so'm"
        return "Kurs mavjud emas"
    get_price.short_description = "Narxi (so'm)"


@admin.register(ConversionRate)
class ConversionRateAdmin(admin.ModelAdmin):
    list_display = ("coin_to_score", "coin_to_money", "updated_at")
    readonly_fields = ("updated_at",)



@admin.register(Coupon_Tutor_Student)
class Coupon_Tutor_StudentAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'discount_percent',
        'valid_from',
        'valid_until',

        'is_active',

    )




@admin.register(SystemCoupon)
class SystemCouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percent', 'valid_until', 'is_active')
    list_filter = ('is_active', 'valid_until')
    search_fields = ('code',)
    ordering = ('-valid_until',)