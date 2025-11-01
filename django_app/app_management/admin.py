from django.contrib import admin
from .models import SystemSettings, FAQ, Product, ReferralAndCouponSettings, Banner, Coupon_Tutor_Student, SystemCoupon,ConversionRate, SolutionStatus
from modeltranslation.admin import TranslationAdmin
from django.utils.html import format_html

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
    list_display = ['name_uz', 'name_ru', 'coin', 'count','get_price', 'image_tag']
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