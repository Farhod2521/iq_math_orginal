from django.contrib import admin
from modeltranslation.admin import TranslationAdmin

from .models import Subject, Topic, Question


@admin.register(Subject)
class SubjectAdmin(TranslationAdmin):
    list_display = ('name', )


@admin.register(Topic)
class TopicAdmin(TranslationAdmin):
    list_display = ('name', )


@admin.register(Question)
class QuestionAdmin(TranslationAdmin):
    list_display = ('id', "question_text" )
