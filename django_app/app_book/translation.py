from modeltranslation.translator import translator, TranslationOptions
from .models import Category, Tag, Book


class CategoryTranslationOptions(TranslationOptions):
    fields = ('name',)


translator.register(Category, CategoryTranslationOptions)


class TagTranslationOptions(TranslationOptions):
    fields = ('name',)


translator.register(Tag, TagTranslationOptions)


class BookTranslationOptions(TranslationOptions):
    fields = ('name', 'description')


translator.register(Book, BookTranslationOptions)
