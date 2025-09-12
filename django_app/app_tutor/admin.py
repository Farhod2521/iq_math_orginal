from django.contrib import admin

from .models import TutorCouponTransaction

@admin.register(TutorCouponTransaction)
class TutorCouponTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'student', 
        'tutor', 
        'coupon', 
        'payment_amount', 
        'student_cashback_amount', 
        'teacher_cashback_amount', 
        'used_at'
    )
    list_filter = ('tutor', 'used_at', 'coupon')
    search_fields = ('student__user__first_name', 'student__user__last_name', 'tutor__user__first_name', 'tutor__user__last_name', 'coupon__code')
    readonly_fields = ('used_at',)
    ordering = ('-used_at',)