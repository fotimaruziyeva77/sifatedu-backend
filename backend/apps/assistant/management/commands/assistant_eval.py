"""AI maslahatchi sifatini haqiqiy Claude bilan tekshirish (pul sarflaydi: ~$0,2–0,5).

    docker compose exec backend python manage.py assistant_eval
    docker compose exec backend python manage.py assistant_eval --only uz --show

Har bir ssenariy tranzaksiya ichida bajariladi va oxirida bekor qilinadi: suhbat va arizalar
bazada qolmaydi, menejerlarga xabar ketmaydi.
"""

from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.test import override_settings

from apps.assistant.agent import respond
from apps.assistant.evals import SCENARIOS, check
from apps.assistant.models import Conversation
from apps.assistant.service import add_user_message


class Command(BaseCommand):
    help = "AI maslahatchini 3 tildagi ssenariylar bilan tekshiradi."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--only", help="Ssenariy ID boshlanishi, masalan uz yoki ru-narx")
        parser.add_argument("--show", action="store_true", help="Javoblarni to'liq chiqarish")

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.ANTHROPIC_API_KEY:
            raise CommandError("ANTHROPIC_API_KEY kerak: eval haqiqiy Claude bilan ishlaydi.")
        prefix = options.get("only") or ""
        scenarios = [scenario for scenario in SCENARIOS if scenario.id.startswith(prefix)]
        passed, total_cost = 0, Decimal(0)
        for scenario in scenarios:
            # Eval har doim haqiqiy Claude bilan: test rejimi yoqilgan bo'lsa ham.
            with override_settings(ASSISTANT_DRY_RUN=False), transaction.atomic():
                conversation = Conversation.objects.create(locale=scenario.locale)
                for text in scenario.turns:
                    add_user_message(conversation, text)
                    respond(conversation)
                conversation.refresh_from_db()
                problems = check(scenario, conversation)
                replies = [
                    message.text
                    for message in conversation.messages.filter(role="ASSISTANT")
                    if message.text
                ]
                total_cost += conversation.cost_usd
                transaction.set_rollback(True)

            passed += not problems
            mark = self.style.SUCCESS("✓") if not problems else self.style.ERROR("✗")
            last = replies[-1] if replies else ""
            summary = last if options["show"] else last[:110].replace("\n", " ")
            self.stdout.write(f"{mark} {scenario.id:<22} ${conversation.cost_usd:.4f}  {summary}")
            for problem in problems:
                self.stdout.write(f"    – {problem}")
        self.stdout.write(f"\n{passed}/{len(scenarios)} o'tdi · jami ${total_cost:.4f}")
