from modeltranslation.translator import translator, TranslationOptions
from .models import (
    SubscriptionBenefit, SubscriptionCategory
    )

class SubscriptionBenefitTranslationOptions(TranslationOptions):
    fields = ('title', "description",)
translator.register(SubscriptionBenefit, SubscriptionBenefitTranslationOptions)




class SubscriptionCategoryTranslationOptions(TranslationOptions):
    fields = ('title',)
translator.register(SubscriptionCategory, SubscriptionCategoryTranslationOptions)
