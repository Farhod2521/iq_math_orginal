from django.contrib import admin
from .models import SubscriptionSetting, Subscription, Payment, SubscriptionPlan, SubscriptionCategory, SubscriptionBenefit




@admin.register(SubscriptionBenefit)
class SubscriptionBenefitAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = ("title",)
    ordering = ("-created_at",)


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




    
from decimal import Decimal
@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "get_plan_name",
        "price_per_month",
        "discount_percent",
        "get_discounted_price",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
        "months",
        "category",
    )

    search_fields = (
        "name",
    )

    ordering = ("months",)

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    filter_horizontal = (
        "benefits",   # 🔥 ManyToMany qulay select
    )

    fieldsets = (
        ("Asosiy maʼlumotlar", {
            "fields": (
                "name",
                "category",
                "months",
                "is_active",
            )
        }),
        ("Narx va chegirma", {
            "fields": (
                "price_per_month",
                "discount_percent",
            )
        }),
        ("Kurs ustunliklari", {
            "fields": (
                "benefits",
            )
        }),
        ("Vaqt maʼlumotlari", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    def get_plan_name(self, obj):
        return obj.get_months_display()
    get_plan_name.short_description = "Tarif (oylar)"

    def get_discounted_price(self, obj):
        """
        Oyiga chegirmali narx
        """
        if obj.discount_percent:
            discount = (obj.price_per_month * Decimal(obj.discount_percent)) / Decimal(100)
            return obj.price_per_month - discount
        return obj.price_per_month

    get_discounted_price.short_description = "Chegirmali narx (oyiga)"




 



@admin.register(SubscriptionCategory)
class SubscriptionCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "slug",
        "is_active",
        "created_at",
    )

    list_editable = (
        "is_active",
    )

    list_filter = (
        "is_active",
        "created_at",
    )

    search_fields = (
        "title",
        "slug",
    )

    prepopulated_fields = {
        "slug": ("title",)
    }

    readonly_fields = (
        "created_at",
    )

    fieldsets = (
        (None, {
            "fields": (
                "title",
                "slug",
                "is_active",
            )
        }),
        ("Vaqt ma’lumotlari", {
            "fields": (
                "created_at",
            )
        }),
    )
