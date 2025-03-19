from modeltranslation.translator import translator, TranslationOptions
from .models import Subject, Topic, Question

class SubjectTranslationOptions(TranslationOptions):
    fields = ('name',)

translator.register(Subject, SubjectTranslationOptions)




class TopicTranslationOptions(TranslationOptions):
    fields = ('name',)

translator.register(Topic, TopicTranslationOptions)

class QuestionTranslationOptions(TranslationOptions):
    fields = ('question_text', 'correct_answer')

translator.register(Question, QuestionTranslationOptions)