from django.contrib import admin
from .models import SubscriptionSetting, Subscription, Payment, SubscriptionPlan

@admin.register(SubscriptionSetting)
class SubscriptionSettingAdmin(admin.ModelAdmin):
    list_display = ("id", "free_trial_days",)
    list_display_links = ("id",)  # bu yerda id ni link qilib belgilaymiz
    list_editable = ("free_trial_days",)

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("student", "start_date", "end_date", "is_paid")
    list_filter = ("is_paid", "start_date", "end_date")
    search_fields = ("student__full_name", "student__user__phone")
    autocomplete_fields = ("student",)
    date_hierarchy = "start_date"

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("student", "amount", "payment_date", "status", "transaction_id")
    list_filter = ("status", "payment_date")
    search_fields = ("student__full_name", "transaction_id")
    autocomplete_fields = ("student",)
    date_hierarchy = "payment_date"




    

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        'get_plan_name',
        'price_per_month',
        'discount_percent',
        'get_discounted_price',
        'is_active',
        'created_at',
    )
    list_filter = ('is_active', 'months',)
    search_fields = ('months',)
    ordering = ('months',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('name', 'months', 'price_per_month', 'discount_percent', 'is_active')
        }),
        ('Vaqt maʼlumotlari', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    def get_plan_name(self, obj):
        return obj.get_months_display()
    get_plan_name.short_description = "Tarif nomi (oylar)"

    def get_discounted_price(self, obj):
        discount_amount = (obj.price_per_month * obj.discount_percent) / 100
        return obj.price_per_month - discount_amount
    get_discounted_price.short_description = "Chegirmali narx (oyiga)"



 
