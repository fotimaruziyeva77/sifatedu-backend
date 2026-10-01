from modeltranslation.translator import TranslationOptions, register

from .models import Product


@register(Product)
class ProductTranslation(TranslationOptions):
    fields = ("name", "description")
    required_languages = {"uz": ("name",)}
