from modeltranslation.translator import translator, TranslationOptions
from .models import Product,  FAQ, SystemSettings
class ProductTranslationOptions(TranslationOptions):
    fields = ('name',)

translator.register(Product, ProductTranslationOptions)



class FAQTranslationOptions(TranslationOptions):
    fields = ('question','answer')

translator.register(FAQ, FAQTranslationOptions)



class SystemSettingsTranslationOptions(TranslationOptions):
    fields = ('about',)

translator.register(SystemSettings, SystemSettingsTranslationOptions)