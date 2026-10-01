from modeltranslation.translator import TranslationOptions, register

from .models import Advantage, Concern, FAQItem, HowStep, LegalPage, SiteSettings, Testimonial


@register(SiteSettings)
class SiteSettingsTranslation(TranslationOptions):
    fields = ("hero_title", "hero_subtitle", "about_text", "address", "working_hours")
    required_languages = {"uz": ("hero_title",)}


@register(Concern)
class ConcernTranslation(TranslationOptions):
    fields = ("problem", "answer")
    required_languages = ("uz",)


@register(Advantage)
class AdvantageTranslation(TranslationOptions):
    fields = ("title", "text")
    required_languages = {"uz": ("title",)}


@register(HowStep)
class HowStepTranslation(TranslationOptions):
    fields = ("title", "text")
    required_languages = {"uz": ("title",)}


@register(FAQItem)
class FAQItemTranslation(TranslationOptions):
    fields = ("question", "answer")
    required_languages = ("uz",)


@register(Testimonial)
class TestimonialTranslation(TranslationOptions):
    fields = ("author_role", "text")
    required_languages = {"uz": ("text",)}


@register(LegalPage)
class LegalPageTranslation(TranslationOptions):
    fields = ("title", "body")
    required_languages = ("uz",)
