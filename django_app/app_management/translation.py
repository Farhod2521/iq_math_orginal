from modeltranslation.translator import translator, TranslationOptions
from .models import Product,  FAQ, SystemSettings, Motivation, Elon, Mathematician
class ProductTranslationOptions(TranslationOptions):
    fields = ('name',)

translator.register(Product, ProductTranslationOptions)

class MathematicianTranslationOptions(TranslationOptions):
    fields = (
        'title',
        'subtitle',
        'life_years',
        'description',
    )


translator.register(Mathematician, MathematicianTranslationOptions)

class FAQTranslationOptions(TranslationOptions):
    fields = ('question','answer')

translator.register(FAQ, FAQTranslationOptions)


class MotivationTranslationOptions(TranslationOptions):
    fields = ('title', 'content')

translator.register(Motivation, MotivationTranslationOptions)
class SystemSettingsTranslationOptions(TranslationOptions):
    fields = ('about',)

translator.register(SystemSettings, SystemSettingsTranslationOptions)



class ElonTranslationOptions(TranslationOptions):
    fields = ('title', 'text')


translator.register(Elon, ElonTranslationOptions)