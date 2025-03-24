from django.contrib import admin
from modeltranslation.admin import TranslationAdmin
from django.utils.safestring import mark_safe

from .models import Subject, Topic, Question, Chapter, Subject_Category


@admin.register(Subject_Category)
class SubjectCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Subject)
class SubjectAdmin(TranslationAdmin):
    list_display = ('name', 'classes', 'category')
    list_filter = ('category', 'classes')
    search_fields = ('name',)
    raw_id_fields = ('teachers',)
    prepopulated_fields = {'name': ('category',)}  # Avtomatik nom yaratish


@admin.register(Chapter)
class ChapterAdmin(TranslationAdmin):
    list_display = ('name', 'subject')
    list_filter = ('subject',)
    search_fields = ('name',)


class QuestionInline(admin.TabularInline):  
    model = Question
    extra = 1  # 1 dona bo‘sh forma qo‘shiladi
    fields = ('question_text', 'correct_answer', 'level')


@admin.register(Topic)
class TopicAdmin(TranslationAdmin):
    list_display = ('name', 'chapter')
    list_filter = ('chapter',)
    search_fields = ('name',)
    inlines = [QuestionInline]  # `Question` qo‘shishni osonlashtiradi


@admin.register(Question)
class QuestionAdmin(TranslationAdmin):
    list_display = ("id", "formatted_question_text", "topic", "level")
    list_filter = ("topic", "level")
    search_fields = ("question_text",)

    def formatted_question_text(self, obj):
        return mark_safe(obj.question_text)  

    formatted_question_text.short_description = "Savol matni"

    class Media:
        js = ('https://polyfill.io/v3/polyfill.min.js?features=es6',
              'https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js')
