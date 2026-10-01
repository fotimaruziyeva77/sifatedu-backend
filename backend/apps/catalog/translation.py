from modeltranslation.translator import TranslationOptions, register

from .models import Category, Course, Instructor, Lesson, Module


@register(Category)
class CategoryTranslation(TranslationOptions):
    fields = ("name",)
    required_languages = ("uz",)


@register(Instructor)
class InstructorTranslation(TranslationOptions):
    fields = ("position", "bio")


@register(Course)
class CourseTranslation(TranslationOptions):
    fields = ("title", "short_description", "description")
    required_languages = ("uz",)


@register(Module)
class ModuleTranslation(TranslationOptions):
    fields = ("title", "summary")
    required_languages = {"uz": ("title",)}


@register(Lesson)
class LessonTranslation(TranslationOptions):
    fields = ("title", "summary")
    required_languages = {"uz": ("title",)}
