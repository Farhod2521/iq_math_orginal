from django.contrib import admin
from modeltranslation.admin import TranslationAdmin
from .models import Student, User, UserSMSAttempt, Class,Teacher
from django.contrib.admin.models import LogEntry


##########################  Teacher ##################################################
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'region', 'districts', "teacher_date", 'status', 'user_phone')
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





class UserAdmin(admin.ModelAdmin):
    list_filter = ('phone',  'sms_code',)  # Status bo‘yicha filter qo‘shish
admin.site.register(User, UserAdmin)


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('action_time', 'user', 'content_type', 'object_repr', 'action_flag', 'change_message')
    list_filter = ('action_time', 'user', 'content_type', 'action_flag')



# admin.site.register(UserSMSAttempt)
admin.site.register(Class)
