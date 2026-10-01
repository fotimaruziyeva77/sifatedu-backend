from rest_framework import serializers

from apps.catalog.serializers import CourseCardSerializer, InstructorCardSerializer
from apps.core.serializers import ReadOnlyModelSerializer

from .models import (
    Advantage,
    Concern,
    FAQItem,
    HowStep,
    LegalPage,
    SiteSettings,
    Testimonial,
)


class SocialsSerializer(serializers.Serializer):
    telegram = serializers.URLField(source="telegram_url")
    instagram = serializers.URLField(source="instagram_url")
    youtube = serializers.URLField(source="youtube_url")
    facebook = serializers.URLField(source="facebook_url")


class SectionsSerializer(serializers.Serializer):
    stats = serializers.BooleanField(source="show_stats")
    instructors = serializers.BooleanField(source="show_instructors")
    testimonials = serializers.BooleanField(source="show_testimonials")


class SiteSettingsSerializer(ReadOnlyModelSerializer):
    socials = SocialsSerializer(source="*")
    sections = SectionsSerializer(source="*")
    payments_enabled = serializers.SerializerMethodField()
    assistant_enabled = serializers.SerializerMethodField()

    class Meta:
        model = SiteSettings
        fields = (
            "payments_enabled",
            "assistant_enabled",
            "hero_title",
            "hero_subtitle",
            "about_text",
            "promo_video",
            "promo_poster",
            "phone",
            "email",
            "address",
            "working_hours",
            "socials",
            "sections",
        )

    def get_payments_enabled(self, obj: SiteSettings) -> bool:
        """Click kalitlari yo'q bo'lsa, saytda sotib olish tugmasi ko'rinmaydi."""
        from apps.payments import click

        return click.configured()

    def get_assistant_enabled(self, obj: SiteSettings) -> bool:
        """AI chat saytda ko'rinadimi: admin'da yoqilgan va Claude kaliti (yoki test rejimi) bor."""
        from apps.assistant.views import chat_enabled

        return chat_enabled()


class StatsSerializer(serializers.Serializer):
    courses = serializers.IntegerField()
    instructors = serializers.IntegerField()
    lessons = serializers.IntegerField()
    students = serializers.IntegerField()


class AdvantageSerializer(ReadOnlyModelSerializer):
    class Meta:
        model = Advantage
        fields = ("id", "icon", "title", "text")


class ConcernSerializer(ReadOnlyModelSerializer):
    class Meta:
        model = Concern
        fields = ("id", "problem", "answer")


class HowStepSerializer(ReadOnlyModelSerializer):
    class Meta:
        model = HowStep
        fields = ("id", "title", "text")


class FAQItemSerializer(ReadOnlyModelSerializer):
    class Meta:
        model = FAQItem
        fields = ("id", "question", "answer")


class TestimonialSerializer(ReadOnlyModelSerializer):
    class Meta:
        model = Testimonial
        fields = ("id", "author_name", "author_role", "text", "avatar")


class LegalPageLinkSerializer(ReadOnlyModelSerializer):
    class Meta:
        model = LegalPage
        fields = ("slug", "title")


class LegalPageSerializer(ReadOnlyModelSerializer):
    class Meta:
        model = LegalPage
        fields = ("slug", "title", "body", "version", "updated_at")


class SitePayloadSerializer(serializers.Serializer):
    settings = SiteSettingsSerializer()
    stats = StatsSerializer()
    advantages = AdvantageSerializer(many=True)
    concerns = ConcernSerializer(many=True)
    steps = HowStepSerializer(many=True)
    faq = FAQItemSerializer(many=True)
    testimonials = TestimonialSerializer(many=True)
    featured_courses = CourseCardSerializer(many=True)
    instructors = InstructorCardSerializer(many=True)
    legal_pages = LegalPageLinkSerializer(many=True)
