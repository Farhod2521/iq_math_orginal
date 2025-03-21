from django.contrib import admin
from modeltranslation.admin import TranslationAdmin

from .models import Subject, Topic, Question, Chapter, Subject_Category

admin.site.register(Subject_Category)

@admin.register(Subject)
class SubjectAdmin(TranslationAdmin):
    list_display = ('name', )


@admin.register(Chapter)
class ChapterAdmin(TranslationAdmin):
    list_display = ('name', )

@admin.register(Topic)
class TopicAdmin(TranslationAdmin):
    list_display = ('name', )

from django.utils.safestring import mark_safe
@admin.register(Question)
class QuestionAdmin(TranslationAdmin):
    list_display = ("id", "question_text")

    def question_text(self, obj):
        return mark_safe(obj.question_text_uz)

    class Media:
        js = ('https://polyfill.io/v3/polyfill.min.js?features=es6', 
              'https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js')
