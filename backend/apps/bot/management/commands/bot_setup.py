"""Bot buyruqlari va tavsifini qayta yozish (matn o'zgarganda).

Markaz botni kabinetda ulaganda bu o'zi bajariladi; buyruq faqat qayta yozish uchun:
`python manage.py tenant_command bot_setup --schema=<markaz>`.
"""

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.bot.appearance import apply_profile
from apps.notifications import telegram


class Command(BaseCommand):
    help = "Bot buyruqlari va tavsifini Telegram'ga yozadi (3 tilda)."

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            apply_profile()
        except telegram.TelegramNotConfiguredError as exc:
            raise CommandError("Bot tokeni kiritilmagan.") from exc
        except (OSError, telegram.TelegramError) as exc:
            raise CommandError(f"Telegram javob bermadi: {exc}") from exc
        self.stdout.write(self.style.SUCCESS("Bot buyruqlari va tavsifi yozildi (uz, ru, en)."))
