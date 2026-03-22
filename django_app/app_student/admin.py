from django.contrib import admin
from .models import Diagnost_Student, TopicProgress, StudentScore, StudentScoreLog, ChapterProgress, ProductExchange, TopicHelpRequestIndependent, StudentDailyCoinLog
from modeltranslation.admin import TranslationAdmin

admin.site.register(Diagnost_Student)
admin.site.register(ProductExchange)
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
    list_display = ('get_student_name', 'award_type', 'get_subject', 'get_question_uz', 'awarded_at')
    list_filter = ('award_type', 'awarded_at')
    search_fields = ('student_score__student__full_name', 'student_score__student__user__phone')
    ordering = ('-awarded_at',)

    @admin.display(description="O'quvchi", ordering='student_score__student__full_name')
    def get_student_name(self, obj):
        return obj.student_score.student.full_name

    @admin.display(description="Fan")
    def get_subject(self, obj):
        subject = obj.question.topic.chapter.subject
        sinf = subject.classes.name if subject.classes else ''
        return f"{sinf} {subject.name}".strip()

    @admin.display(description="Savol (O'zbekcha)")
    def get_question_uz(self, obj):
        text = obj.question.question_text_uz or obj.question.question_text or ''
        from django.utils.html import strip_tags
        clean = strip_tags(str(text))
        return clean[:80] + '...' if len(clean) > 80 else clean


@admin.register(StudentDailyCoinLog)
class StudentDailyCoinLogAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'coin_count')
    list_filter = ('date',)
    search_fields = ('student__full_name', 'student__user__phone')
    ordering = ('-date', '-coin_count')
    readonly_fields = ('student', 'date', 'coin_count')







@admin.register(TopicHelpRequestIndependent)
class TopicHelpRequestIndependentAdmin(TranslationAdmin):
    list_display = ('student', 'subject', 'teacher', 'level', 'reviewed_at', 'created_at')
    list_filter = ('subject', 'teacher', 'level', 'created_at')
    search_fields = ('student__user__phone', 'teacher__full_name', 'commit_uz', 'commit_ru')
    readonly_fields = ('created_at', 'reviewed_at')




