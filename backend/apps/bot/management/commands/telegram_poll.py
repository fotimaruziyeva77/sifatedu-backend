"""Local sinov: botga kelgan xabar va tugmalarni long polling bilan olib, botga beradi.

Telegram webhook bilan polling bir vaqtda ishlamaydi. Webhook o'rnatilgan bo'lsa (production),
buyruq to'xtaydi — `--force` bilan webhook o'chiriladi.
"""

import logging
import time
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.bot.router import handle_update
from apps.notifications import telegram

logger = logging.getLogger(__name__)
ALLOWED_UPDATES = ["message", "callback_query", "my_chat_member"]
POLL_SECONDS = 25
# Tarmoq uzilsa (Wi-Fi, Docker qayta ishga tushdi) — kutib, qayta so'raladi, buyruq to'xtamaydi.
RETRY_SECONDS = 5


class Command(BaseCommand):
    help = "Telegram botni local'da sinash (long polling)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--force", action="store_true", help="O'rnatilgan webhook'ni o'chirish")
        parser.add_argument("--once", action="store_true", help="Bir marta so'rab to'xtash")

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            info = self.patiently("getWebhookInfo", {})
        except telegram.TelegramNotConfiguredError as exc:
            raise CommandError("TELEGRAM_BOT_TOKEN bo'sh.") from exc
        if info.get("url"):
            if not options["force"]:
                raise CommandError(
                    f"Webhook o'rnatilgan: {info['url']}. "
                    "Polling uchun --force bilan ishga tushiring."
                )
            self.patiently("deleteWebhook", {})
        self.stdout.write("Bot xabarlarini kutyapman… (to'xtatish: Ctrl+C)")
        offset = None
        while True:
            updates = self.patiently(
                "getUpdates",
                {"timeout": POLL_SECONDS, "offset": offset, "allowed_updates": ALLOWED_UPDATES},
                timeout=POLL_SECONDS + 10,
            )
            for update in updates or []:
                offset = update["update_id"] + 1
                try:
                    handle_update(update)
                except Exception:
                    logger.exception("Telegram xabari qayta ishlanmadi")
            if options["once"]:
                return

    def patiently(self, method: str, payload: dict[str, Any], **kwargs: Any) -> Any:
        """Telegram so'rovi: tarmoq xatosi yoki Telegram 5xx/429 bo'lsa — kutib, qayta."""
        while True:
            try:
                return telegram.call(method, payload, **kwargs)
            except telegram.TelegramError as exc:
                if exc.code != 429 and exc.code < 500:
                    raise
                wait = exc.retry_after or RETRY_SECONDS
            except OSError as exc:
                wait = RETRY_SECONDS
                logger.warning("Telegram'ga ulanib bo'lmadi (%s), %s s dan keyin qayta", exc, wait)
            time.sleep(wait)
