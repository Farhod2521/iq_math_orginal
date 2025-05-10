from django.contrib import admin
from .models import SystemSettings, FAQ, Product

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



@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'ball']
    search_fields = ['name']