from django.contrib import admin
from .models import Diagnost_Student, TopicProgress, StudentScore, StudentScoreLog, ChapterProgress


admin.site.register(Diagnost_Student)
# Register your models here.






@admin.register(ChapterProgress)
class ChapterProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'chapter', 'progress_percentage', 'updated_at')
    list_filter = ('chapter', 'updated_at')
    search_fields = ('user__full_name', 'chapter__name')  # Student modelda full_name bo‘lsa
    ordering = ('-updated_at',)


@admin.register(TopicProgress)
class TopicProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'topic', 'score', 'is_unlocked', 'completed_at')
    list_filter = ('is_unlocked', 'completed_at')
    search_fields = ('user__user__username', 'topic__name')
    ordering = ('-completed_at',)
    verbose_name = "Mavzu bo‘yicha yutuq"
    verbose_name_plural = "Mavzular bo‘yicha yutuqlar"


@admin.register(StudentScore)
class StudentScoreAdmin(admin.ModelAdmin):
    list_display = ('student', 'score', 'created_at')
    search_fields = ('student__user__username',)
    ordering = ('-score',)
    verbose_name = "Talaba bali"
    verbose_name_plural = "Talabalar ballari"


@admin.register(StudentScoreLog)
class StudentScoreLogAdmin(admin.ModelAdmin):
    list_display = ('student_score', 'question', 'awarded_at')
    search_fields = ('student_score__student__user__username', 'question__question_text_uz')
    ordering = ('-awarded_at',)
    verbose_name = "Ball olish tarixi"
    verbose_name_plural = "Ballar olish tarixi"