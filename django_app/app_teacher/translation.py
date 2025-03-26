from modeltranslation.translator import translator, TranslationOptions
from .models import Subject, Topic, Question, Chapter

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
    fields = ('question_text', 'correct_answer')

translator.register(Question, QuestionTranslationOptions)