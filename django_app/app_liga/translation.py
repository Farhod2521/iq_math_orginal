from modeltranslation.translator import translator, TranslationOptions

from .models import LigaSeason, LigaQuestion, LigaChoice


class LigaSeasonTranslationOptions(TranslationOptions):
    fields = ('description',)


translator.register(LigaSeason, LigaSeasonTranslationOptions)


class LigaQuestionTranslationOptions(TranslationOptions):
    fields = ('question_text',)


translator.register(LigaQuestion, LigaQuestionTranslationOptions)


class LigaChoiceTranslationOptions(TranslationOptions):
    fields = ('text',)


translator.register(LigaChoice, LigaChoiceTranslationOptions)
