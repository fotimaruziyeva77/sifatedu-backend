"""Telegram bot webhook'ini boshqarish: `set` (production), `delete`, `info`."""

import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.integrations import conf
from apps.integrations.services import set_webhook, webhook_url
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
            account = conf.telegram()
            if not account.webhook_secret:
                raise CommandError("Webhook siri yo'q: botni kabinetda qayta ulang.")
            if not set_webhook(account.token, account.webhook_secret):
                raise CommandError(f"Telegram faqat https manzilga yuboradi: {webhook_url()}.")
            self.stdout.write(self.style.SUCCESS(f"Webhook o'rnatildi: {webhook_url()}"))
        except telegram.TelegramNotConfiguredError as exc:
            raise CommandError("Bot tokeni kiritilmagan.") from exc
