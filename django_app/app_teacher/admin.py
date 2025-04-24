from django.contrib import admin
from modeltranslation.admin import TranslationAdmin, TranslationTabularInline
from django.utils.safestring import mark_safe

from .models import (
    Topic, Question,
                      Chapter,  Choice, CompositeSubQuestion
                      )

from django_app.app_user.models import  Subject, Subject_Category
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
    fields = ('question_text', 'level')


@admin.register(Topic)
class TopicAdmin(TranslationAdmin):
    list_display = ('name', 'chapter')
    list_filter = ('chapter',)
    search_fields = ('name',)
    inlines = [QuestionInline]  # `Question` qo‘shishni osonlashtiradi


class ChoiceInline(TranslationTabularInline):
    model = Choice
    extra = 1


class CompositeSubQuestionInline(TranslationTabularInline):
    model = CompositeSubQuestion
    extra = 1

from django.utils.safestring import mark_safe

class QuestionAdmin(TranslationAdmin):
    list_display = ('rendered_question_text', 'question_type', 'level')
    list_filter = ('question_type', 'level')
    search_fields = ('question_text',)
    inlines = [ChoiceInline, CompositeSubQuestionInline]

    def rendered_question_text(self, obj):
        return mark_safe(obj.question_text)
    rendered_question_text.short_description = "Savol"

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
