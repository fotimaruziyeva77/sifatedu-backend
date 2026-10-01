from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "kind", "title", "body", "link", "created_at", "read_at")
        read_only_fields = fields


class NotificationReadSerializer(serializers.Serializer):
    """`ids` berilmasa — hammasi o'qilgan deb belgilanadi."""

    ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, max_length=100
    )


class UnreadSerializer(serializers.Serializer):
    unread = serializers.IntegerField()


class TelegramStatusSerializer(serializers.Serializer):
    available = serializers.BooleanField(help_text="Bot sozlangan: ulash tugmasi ko'rsatiladi.")
    connected = serializers.BooleanField()
    notify = serializers.BooleanField(help_text="Foydalanuvchi Telegram xabarlarini o'chirmagan.")
    blocked = serializers.BooleanField(help_text="Telegram bot yozishiga ruxsat bermayapti.")


class NotificationSettingsSerializer(serializers.Serializer):
    telegram = TelegramStatusSerializer()
    marketing_consent = serializers.BooleanField()


class NotificationSettingsUpdateSerializer(serializers.Serializer):
    telegram_notify = serializers.BooleanField(required=False)
    marketing_consent = serializers.BooleanField(required=False)


class TelegramConnectSerializer(serializers.Serializer):
    url = serializers.URLField()
    expires_in = serializers.IntegerField(help_text="Havola necha soniya amal qiladi.")
