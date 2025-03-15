from django.contrib import admin
from modeltranslation.admin import TranslationAdmin
from .models import Student, User, UserSMSAttempt


# @admin.register(Student)
# class StudentAdmin(TranslationAdmin):
#     list_display = ('full_name', 'region', 'districts', 'address', 'brithday', 'academy_or_school', 'class_name', 'status')



class UserAdmin(admin.ModelAdmin):
    list_filter = ('phone',  'sms_code',)  # Status bo‘yicha filter qo‘shish
 
admin.site.register(User, UserAdmin)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'region', 'districts', "student_date", 'status', 'user_phone')
    list_filter = ('full_name', 'region', 'districts', "student_date", 'status')
    search_fields = ('full_name', 'region', 'districts', "student_date")

    def user_phone(self, obj):
        return obj.user.phone if obj.user else "-"
    user_phone.short_description = 'Phone'  # Admin panelda sarlavha sifatida chiqadi
admin.site.register(Student, StudentAdmin)


admin.site.register(UserSMSAttempt)




from django.contrib.admin.models import LogEntry

@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('action_time', 'user', 'content_type', 'object_repr', 'action_flag', 'change_message')
    list_filter = ('action_time', 'user', 'content_type', 'action_flag')