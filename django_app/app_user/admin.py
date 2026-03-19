from django.contrib import admin
from modeltranslation.admin import TranslationAdmin
from .models import Student, User, UserSMSAttempt, Class,Teacher, Referral, Parent, Tutor
from django.contrib.admin.models import LogEntry


##########################  Teacher ##################################################
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'region', 'districts', "teacher_date", 'status', 'user_phone', "support")
    list_filter = ('full_name', 'region', 'districts', "teacher_date", 'status')
    search_fields = ('full_name', 'region', 'districts', "teacher_date")

    def user_phone(self, obj):
        return obj.user.phone if obj.user else "-"
    user_phone.short_description = 'Phone' 
admin.site.register(Teacher, TeacherAdmin)


##########################  STUDENT ##################################################
class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'region', 'districts', "student_date", 'status', 'user_phone')
    list_filter = ('full_name', 'region', 'districts', "student_date", 'status')
    search_fields = ('full_name', 'region', 'districts', "student_date")

    def user_phone(self, obj):
        return obj.user.phone if obj.user else "-"
    user_phone.short_description = 'Phone' 
admin.site.register(Student, StudentAdmin)


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "user", "parent_date", 'status')
    list_filter = ("region", "districts")
    search_fields = ("full_name", "user__phone", "user__email")
    ordering = ("-parent_date",)



@admin.register(Tutor)
class TutorAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "user", "tutor_date", 'status')
    list_filter = ("region", "districts")
    search_fields = ("full_name", "user__phone", "user__email")
    ordering = ("-tutor_date",)

class UserAdmin(admin.ModelAdmin):
    list_display = ('phone', 'role', 'profile_status', 'sms_confirmed', 'date_joined')
    list_filter = ('role',)
    search_fields = ('phone',)
    ordering = ('-date_joined',)

    def profile_status(self, obj):
        """Profilning tasdiqlangan yoki tasdiqlanmagan holati"""
        from django.utils.html import format_html
        profile = (
            getattr(obj, 'student_profile', None)
            or getattr(obj, 'parent_profile', None)
            or getattr(obj, 'tutor_profile', None)
            or getattr(obj, 'teacher_profile', None)
        )
        if profile is None:
            return format_html('<span style="color:gray;">—</span>')
        if profile.status:
            return format_html('<span style="color:green; font-weight:bold;">✔ Tasdiqlangan</span>')
        return format_html('<span style="color:red;">✘ Tasdiqlanmagan</span>')
    profile_status.short_description = 'Status'

    def sms_confirmed(self, obj):
        """SMS kod tozalanganmi — ya'ni tasdiqlangan"""
        from django.utils.html import format_html
        if obj.sms_code:
            return format_html('<span style="color:orange;">⏳ SMS kutilmoqda</span>')
        return format_html('<span style="color:green;">✔</span>')
    sms_confirmed.short_description = 'SMS'

admin.site.register(User, UserAdmin)


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('action_time', 'user', 'content_type', 'object_repr', 'action_flag', 'change_message')
    list_filter = ('action_time', 'user', 'content_type', 'action_flag')



# admin.site.register(UserSMSAttempt)
admin.site.register(Class)



@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('referrer_full_name', 'referred_full_name', 'created_at')
    search_fields = ('referrer__full_name', 'referred__full_name')
    list_filter = ('created_at',)

    def referrer_full_name(self, obj):
        return obj.referrer.full_name
    referrer_full_name.short_description = "Taklif qilgan"

    def referred_full_name(self, obj):
        return obj.referred.full_name
    referred_full_name.short_description = "Taklif qilingan"