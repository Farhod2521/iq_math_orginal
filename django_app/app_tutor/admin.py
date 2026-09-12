from django.contrib import admin

from .models import TutorCouponTransaction, TutorGroup, WithdrawalLimitSettings

@admin.register(TutorCouponTransaction)
class TutorCouponTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'student', 
        'tutor', 
        'coupon', 
        'payment_amount', 
        'cashback_amount', 
        'used_at'
    )
    list_filter = ('tutor', 'used_at', 'coupon')
    search_fields = ('student__user__first_name', 'student__user__last_name', 'tutor__user__first_name', 'tutor__user__last_name', 'coupon__code')
    readonly_fields = ('used_at',)
    ordering = ('-used_at',)



@admin.register(WithdrawalLimitSettings)
class WithdrawalLimitSettingsAdmin(admin.ModelAdmin):
    list_display = ("min_amount", "max_amount", "updated_at")


@admin.register(TutorGroup)
class TutorGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'tutor', 'student_count', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at', 'tutor')
    search_fields = ('name', 'tutor__full_name', 'tutor__identification')
    filter_horizontal = ('students',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    @admin.display(description="O'quvchilar soni")
    def student_count(self, obj):
        return obj.students.count()
