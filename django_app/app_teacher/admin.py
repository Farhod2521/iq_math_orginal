from django.contrib import admin
from modeltranslation.admin import TranslationAdmin, TranslationTabularInline
from django.utils.safestring import mark_safe

from .models import (
    Topic, Question,
                      Chapter,  Choice, CompositeSubQuestion, UnsolvedQuestionReport, Group, GeneratedChoiceOpenAi, GeneratedSubQuestionOpenAi, GeneratedQuestionOpenAi
                      )

from django_app.app_user.models import  Subject, Subject_Category




# 🔹 Variantlar uchun inline admin
class GeneratedChoiceOpenAiInline(admin.TabularInline):
    model = GeneratedChoiceOpenAi
    extra = 1
    fields = ("letter", "text", "is_correct")
    show_change_link = True
    verbose_name = "AI Variant"
    verbose_name_plural = "AI Variantlar"


# 🔹 Sub-savollar uchun inline admin
class GeneratedSubQuestionOpenAiInline(admin.TabularInline):
    model = GeneratedSubQuestionOpenAi
    extra = 1
    fields = ("text1", "correct_answer", "text2")
    show_change_link = True
    verbose_name = "AI Kichik savol"
    verbose_name_plural = "AI Kichik savollar"


# 🔹 Asosiy generatsiya qilingan savollar admini
@admin.register(GeneratedQuestionOpenAi)
class GeneratedQuestionOpenAiAdmin(admin.ModelAdmin):
    list_display = (
        "id", "topic", "base_question", "short_generated_text",
        "created_at", "created_by_ai"
    )
    list_filter = ("topic", "created_by_ai", "created_at")
    search_fields = ("generated_text", "base_question__question_text", "topic__name")
    readonly_fields = ("created_at",)
    inlines = [GeneratedChoiceOpenAiInline, GeneratedSubQuestionOpenAiInline]

    def short_generated_text(self, obj):
        return (obj.generated_text[:80] + "...") if obj.generated_text else "-"
    short_generated_text.short_description = "AI Savol"


# (Ixtiyoriy) alohida model sifatida ham tahrirlash mumkin bo‘lsin
@admin.register(GeneratedChoiceOpenAi)
class GeneratedChoiceOpenAiAdmin(admin.ModelAdmin):
    list_display = ("generated_question", "letter", "short_text", "is_correct")
    list_filter = ("is_correct",)
    search_fields = ("text", "generated_question__generated_text")

    def short_text(self, obj):
        return (obj.text[:80] + "...") if obj.text else "-"
    short_text.short_description = "Variant matni"


@admin.register(GeneratedSubQuestionOpenAi)
class GeneratedSubQuestionOpenAiAdmin(admin.ModelAdmin):
    list_display = ("generated_question", "text1", "correct_answer", "text2")
    search_fields = ("text1", "text2", "correct_answer")




@admin.register(Subject_Category)
class SubjectCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Subject)
class SubjectAdmin(TranslationAdmin):
    list_display = ('name_uz', 'name_ru', 'classes', 'category', 'order', 'active')  # ✅ active qo‘shildi
    list_editable = ('order', 'active')  # ✅ admin ro‘yxat ichida tahrirlash mumkin
    list_filter = ('category', 'classes', 'active')  # ✅ faollik bo‘yicha ham filtrlash
    search_fields = ('name_uz', 'name_ru')
    raw_id_fields = ('teachers',)
    
@admin.register(Chapter)
class ChapterAdmin(TranslationAdmin):
    list_display = ('name_uz','name_ru', 'subject')
    list_filter = ('subject',)
    search_fields = ('name_uz','name_ru',)


class QuestionInline(admin.TabularInline):  
    model = Question
    extra = 1  # 1 dona bo‘sh forma qo‘shiladi
    fields = ('question_text', 'level')


@admin.register(Topic)
class TopicAdmin(TranslationAdmin):
    list_display = ('name_uz','name_ru', 'chapter')
    list_filter = ('chapter',)
    search_fields = ('name_uz','name_ru',)
    inlines = [QuestionInline]  # `Question` qo‘shishni osonlashtiradi


class ChoiceInline(TranslationTabularInline):
    model = Choice
    extra = 1


class CompositeSubQuestionInline(TranslationTabularInline):
    model = CompositeSubQuestion
    extra = 1

from django.utils.safestring import mark_safe

@admin.register(Question)
class QuestionAdmin(TranslationAdmin):
    list_display = ('question_text_uz','question_text_ru', 'question_type', 'level')
    list_filter = ('question_type', 'level')
    search_fields = ('question_text',)
    inlines = [ChoiceInline, CompositeSubQuestionInline]



    class Media:
        js = (
            'https://polyfill.io/v3/polyfill.min.js?features=es6',
            'https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js',
        )


@admin.register(Choice)
class ChoiceAdmin(TranslationAdmin):
    list_display = ('question', 'letter', 'text', 'is_correct')
    list_filter = ('is_correct',)
    search_fields = ('text',)


@admin.register(CompositeSubQuestion)
class CompositeSubQuestionAdmin(TranslationAdmin):
    list_display = ('question', 'text1', 'correct_answer', 'text2')
    search_fields = ('text1', 'correct_answer', 'text2')



@admin.register(UnsolvedQuestionReport)
class UnsolvedQuestionReportAdmin(admin.ModelAdmin):
    list_display = (
        'id', 
        'student', 
        'question', 
        'status', 
        'answered_by', 
        'created_at', 
        'answered_at'
        
    )
    list_filter = ('status', 'created_at', 'answered_at')
    search_fields = ('student__full_name', 'question__title', 'message', 'answer')
    autocomplete_fields = ('student', 'teachers', 'answered_by', 'question')
    filter_horizontal = ('teachers',)
    readonly_fields = ('created_at', 'answered_at')
    date_hierarchy = 'created_at'


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'teacher', 'created_at')
    search_fields = ('name', 'teacher__full_name')
    list_filter = ('teacher',)
    filter_horizontal = ('students',)