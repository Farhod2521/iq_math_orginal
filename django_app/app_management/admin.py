from django.contrib import admin
from .models import SystemSettings, FAQ, Product, ReferralAndCouponSettings
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


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question']
    search_fields = ['question', 'answer']

@admin.register(ReferralAndCouponSettings)
class ReferralAndCouponSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'referral_bonus_points',
        'coupon_discount_percent',
        'coupon_valid_days',
        'updated_at',
    )
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': (
                'referral_bonus_points',
                'coupon_discount_percent',
                'coupon_valid_days',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def has_add_permission(self, request):
        # Faqat bitta sozlama bo'lishini istasangiz — singleton tarzida
        if ReferralAndCouponSettings.objects.exists():
            return False
        return True


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