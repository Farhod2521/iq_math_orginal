from django.contrib import admin
from .models import SystemSettings, FAQ, Product, ReferralAndCouponSettings, Banner, Coupon, SystemCoupon
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
     
        'coupon_discount_percent',
        'coupon_valid_days',
        'updated_at',
    )



@admin.register(Product)
class ProductAdmin(TranslationAdmin):  # model.ModelAdmin o'rniga TranslationAdmin ishlatiladi
    list_display = ['name_uz','name_ru', 'coin', 'image_tag']
    search_fields = ['name_uz','name_ru']
    readonly_fields = ['image_tag']

    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />', obj.image.url)
        return "-"
    image_tag.short_description = 'Rasm'



@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'discount_percent',
        'valid_from',
        'valid_until',
        'created_by',
        'is_active',
        'created_at'
    )
    list_filter = (
        'is_active',
        'created_by_teacher',
        'created_by_student',
    )
    search_fields = (
        'code',
        'created_by_teacher__full_name',
        'created_by_student__full_name',
    )

    def created_by(self, obj):
        if obj.created_by_teacher:
            return f"👨‍🏫 {obj.created_by_teacher.full_name}"
        elif obj.created_by_student:
            return f"🧑‍🎓 {obj.created_by_student.full_name}"
        return "Noma’lum"
    
    created_by.short_description = "Yaratuvchi"


@admin.register(SystemCoupon)
class SystemCouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percent', 'valid_until', 'is_active')
    list_filter = ('is_active', 'valid_until')
    search_fields = ('code',)
    ordering = ('-valid_until',)