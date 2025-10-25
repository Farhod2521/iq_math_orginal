from django.contrib import admin
from modeltranslation.admin import TranslationAdmin, TranslationTabularInline
from django.utils.safestring import mark_safe

from .models import (
    Topic, Question,
                      Chapter,  Choice, CompositeSubQuestion, UnsolvedQuestionReport, Group, GeneratedChoiceOpenAi, GeneratedSubQuestionOpenAi, GeneratedQuestionOpenAi
                      )

from django_app.app_user.models import  Subject, Subject_Category




# 🔹 Variantlar uchun inline admin (A, B, C, D)
class GeneratedChoiceOpenAiInline(admin.TabularInline):
    model = GeneratedChoiceOpenAi
    extra = 1
    fields = ("letter", "text_uz", "text_ru", "is_correct")
    show_change_link = True
    verbose_name = "AI Variant"
    verbose_name_plural = "AI Variantlar"


# 🔹 Sub-savollar uchun inline admin (bir nechta inputli savollar uchun)
class GeneratedSubQuestionOpenAiInline(admin.TabularInline):
    model = GeneratedSubQuestionOpenAi
    extra = 1
    fields = (
        "text1_uz", "text1_ru",
        "correct_answer_uz", "correct_answer_ru",
        "text2_uz", "text2_ru"
    )
    show_change_link = True
    verbose_name = "AI Kichik savol"
    verbose_name_plural = "AI Kichik savollar"


# 🔹 Asosiy generatsiya qilingan savollar admini
@admin.register(GeneratedQuestionOpenAi)
class GeneratedQuestionOpenAiAdmin(admin.ModelAdmin):
    list_display = (
        "id", "topic", "question_type",
        "short_generated_text_uz", "short_generated_text_ru",
        "created_at", "created_by_ai"
    )
    list_filter = ("topic", "question_type", "created_by_ai", "created_at")
    search_fields = (
        "generated_text_uz", "generated_text_ru",
        "topic__name"
    )
    readonly_fields = ("created_at",)
    inlines = [GeneratedChoiceOpenAiInline, GeneratedSubQuestionOpenAiInline]
    list_per_page = 25

    def short_generated_text_uz(self, obj):
        return (obj.generated_text_uz[:60] + "...") if obj.generated_text_uz else "-"
    short_generated_text_uz.short_description = "Savol (UZ)"

    def short_generated_text_ru(self, obj):
        return (obj.generated_text_ru[:60] + "...") if obj.generated_text_ru else "-"
    short_generated_text_ru.short_description = "Savol (RU)"


# 🔹 Alohida model sifatida ham ko‘rish uchun (variantlar)
@admin.register(GeneratedChoiceOpenAi)
class GeneratedChoiceOpenAiAdmin(admin.ModelAdmin):
    list_display = ("generated_question", "letter", "short_text_uz", "short_text_ru", "is_correct")
    list_filter = ("is_correct",)
    search_fields = ("text_uz", "text_ru", "generated_question__generated_text_uz")
    list_per_page = 30

    def short_text_uz(self, obj):
        return (obj.text_uz[:60] + "...") if obj.text_uz else "-"
    short_text_uz.short_description = "Variant (UZ)"

    def short_text_ru(self, obj):
        return (obj.text_ru[:60] + "...") if obj.text_ru else "-"
    short_text_ru.short_description = "Variant (RU)"


# 🔹 Kichik (sub) savollar admini
@admin.register(GeneratedSubQuestionOpenAi)
class GeneratedSubQuestionOpenAiAdmin(admin.ModelAdmin):
    list_display = (
        "generated_question",
        "short_text1_uz", "short_text1_ru",
        "correct_answer_uz", "correct_answer_ru"
    )
    search_fields = (
        "text1_uz", "text1_ru",
        "correct_answer_uz", "correct_answer_ru"
    )
    list_per_page = 30

    def short_text1_uz(self, obj):
        return (obj.text1_uz[:60] + "...") if obj.text1_uz else "-"
    short_text1_uz.short_description = "Kichik savol (UZ)"

    def short_text1_ru(self, obj):
        return (obj.text1_ru[:60] + "...") if obj.text1_ru else "-"
    short_text1_ru.short_description = "Kichik savol (RU)"




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