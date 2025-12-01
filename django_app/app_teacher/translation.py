from modeltranslation.translator import translator, TranslationOptions
from .models import (
    Subject, Topic, Question, Chapter, CompositeSubQuestion, Choice
    )
from django_app.app_user.models import Subject_Category
class Subject_CategoryTranslationOptions(TranslationOptions):
    fields = ('name',)

translator.register(Subject_Category, Subject_CategoryTranslationOptions)

class SubjectTranslationOptions(TranslationOptions):
    fields = ('name',)

translator.register(Subject, SubjectTranslationOptions)
class ChapterTranslationOptions(TranslationOptions):
    fields = ('name',)
translator.register(Chapter, ChapterTranslationOptions)

class TopicTranslationOptions(TranslationOptions):
    fields = ('name','content',)

translator.register(Topic, TopicTranslationOptions)

class QuestionTranslationOptions(TranslationOptions):
    fields = ('question_text', 'correct_text_answer')

translator.register(Question, QuestionTranslationOptions)

class CompositeSubQuestionTranslationOptions(TranslationOptions):
    fields = ('text1', "text2")

translator.register(CompositeSubQuestion, CompositeSubQuestionTranslationOptions)

class ChoiceTranslationOptions(TranslationOptions):
    fields = ('text',)  # Faqat text tarjima qilinadi

translator.register(Choice, ChoiceTranslationOptions)