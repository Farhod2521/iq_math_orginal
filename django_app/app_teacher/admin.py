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


@admin.register(Question)
class QuestionAdmin(TranslationAdmin):
    list_display = ('id', "question_text" )
