from modeltranslation.translator import translator, TranslationOptions
from .models import (
    TopicHelpRequestIndependent
    )

class TopicHelpRequestIndependentTranslationOptions(TranslationOptions):
    fields = ('commit',)
translator.register(TopicHelpRequestIndependent, TopicHelpRequestIndependentTranslationOptions)
