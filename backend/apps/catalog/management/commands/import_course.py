"""Kurs dasturini (`backend/content/<kurs>/`) platformaga joylash: modullar, darslar, slaydlar,
testlar va uy vazifalari.

    python manage.py import_course python             # joylash
    python manage.py import_course --all --check      # hamma kurslarni faqat tekshirish
    python manage.py import_course backend --dry-run  # nima o'zgarishini ko'rsatish
"""

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from apps.catalog import courseware


class Command(BaseCommand):
    help = "Kurs dasturini backend/content dan platformaga joylaydi."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("names", nargs="*", help="content/ ichidagi kurs papkalari")
        parser.add_argument("--all", action="store_true", help="hamma kurslar")
        parser.add_argument("--check", action="store_true", help="faqat fayllarni tekshirish")
        parser.add_argument("--dry-run", action="store_true", help="bazaga yozmasdan ko'rsatish")
        parser.add_argument(
            "--replace-tests",
            action="store_true",
            help="testni fayldagisiga almashtirish (urinishlar bo'lmasa)",
        )
        parser.add_argument(
            "--update-homework", action="store_true", help="uy vazifasi matnini yangilash"
        )

    def handle(self, *args: Any, **options: Any) -> None:
        names = courseware.course_names() if options["all"] else options["names"]
        if not names:
            raise CommandError(f"Kurs nomi kerak. Bor: {', '.join(courseware.course_names())}")
        try:
            contents = [courseware.read_course(name) for name in names]
        except courseware.ContentError as exc:
            raise CommandError(str(exc)) from exc
        found = [problem for content in contents for problem in courseware.problems(content)]
        if found:
            raise CommandError("Fayllarda xato:\n" + "\n".join(found))
        for content in contents:
            lessons = sum(len(module.lessons) for module in content.modules)
            self.stdout.write(
                f"{content.name} → «{content.slug}»: {len(content.modules)} modul, {lessons} dars"
            )
            if options["check"]:
                continue
            try:
                report = courseware.apply(
                    content,
                    replace_tests=options["replace_tests"],
                    update_homework=options["update_homework"],
                    dry_run=options["dry_run"],
                )
            except courseware.ContentError as exc:
                raise CommandError(str(exc)) from exc
            for line in report.lines:
                self.stdout.write(f"  {line}")
        self.stdout.write(self.style.SUCCESS("Tayyor."))
