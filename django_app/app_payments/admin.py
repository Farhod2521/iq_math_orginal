from django.contrib import admin
from .models import SubscriptionSetting, Subscription, Payment

@admin.register(SubscriptionSetting)
class SubscriptionSettingAdmin(admin.ModelAdmin):
    list_display = ("free_trial_days",)
    list_editable = ("free_trial_days",)
    verbose_name = "Obuna sozlamasi"

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("student", "start_date", "end_date", "is_paid")
    list_filter = ("is_paid", "start_date", "end_date")
    search_fields = ("student__full_name", "student__user__username")
    autocomplete_fields = ("student",)
    date_hierarchy = "start_date"

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("student", "amount", "payment_date", "status", "transaction_id")
    list_filter = ("status", "payment_date")
    search_fields = ("student__full_name", "transaction_id")
    autocomplete_fields = ("student",)
    date_hierarchy = "payment_date"
