"""Telegram bot webhook'ini boshqarish: `set` (production), `delete`, `info`."""

import json
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.notifications import telegram


class Command(BaseCommand):
    help = "Telegram bot webhook'i: set | delete | info"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("action", choices=["set", "delete", "info"])

    def handle(self, *args: Any, **options: Any) -> None:
        action = options["action"]
        try:
            if action == "info":
                info = telegram.call("getWebhookInfo", {})
                self.stdout.write(json.dumps(info, ensure_ascii=False, indent=2))
                return
            if action == "delete":
                telegram.call("deleteWebhook", {})
                self.stdout.write(self.style.SUCCESS("Webhook o'chirildi."))
                return
            secret = settings.TELEGRAM_WEBHOOK_SECRET
            if not secret:
                raise CommandError(
                    "TELEGRAM_WEBHOOK_SECRET bo'sh: backend/.env ga tasodifiy qator yozing."
                )
            url = f"{settings.APP_URL.rstrip('/')}/api/v1/bot/webhook/"
            if not url.startswith("https://"):
                raise CommandError(f"Telegram faqat https manzilga yuboradi: {url} (APP_URL).")
            telegram.call(
                "setWebhook",
                {
                    "url": url,
                    "secret_token": secret,
                    "allowed_updates": ["message", "callback_query", "my_chat_member"],
                },
            )
            self.stdout.write(self.style.SUCCESS(f"Webhook o'rnatildi: {url}"))
        except telegram.TelegramNotConfiguredError as exc:
            raise CommandError("TELEGRAM_BOT_TOKEN bo'sh.") from exc
