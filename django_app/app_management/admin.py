from django.contrib import admin
from .models import  (
    Motivation, SystemSettings, FAQ, Product, ReferralAndCouponSettings, 
    Banner, Coupon_Tutor_Student, SystemCoupon,ConversionRate, SolutionStatus,
    Elon, Category, Tag, UploadedFile
    )
from modeltranslation.admin import TranslationAdmin
from django.utils.html import format_html




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
    list_display = ['__str__', 'updated_at']
    readonly_fields = ['updated_at']
    fieldsets = (
        ("Logo", {
            'fields': ('logo',)
        }),
        ("Biz haqimizda", {
            'fields': ('about_uz', 'about_ru')
        }),
        ("Ijtimoiy tarmoqlar", {
            'fields': (
                'instagram_link', 'telegram_link', 'youtube_link',
                'twitter_link', 'facebook_link', 'linkedin_link'
            )
        }),
        ("Shartnomalar", {
            'fields': ('shartnoma_uz', 'shartnoma_ru')
        }),
        ("Tizim holati", {
            'fields': ('updated_at',)
        }),
    )
admin.site.register(Banner)

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