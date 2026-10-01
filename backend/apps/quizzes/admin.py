"""Admin: darsga test, savollarni tez kiritish, variantlar va har savol bo'yicha natija.

O'qituvchi faqat o'z kurslari testlarini ko'radi va o'zgartiradi (catalog/scope.py).
"""

from typing import Any

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db.models import Avg, Count, QuerySet
from django.forms.models import BaseInlineFormSet
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.decorators import display
from unfold.widgets import UnfoldAdminTextareaWidget

from apps.catalog.scope import TeacherScopedAdmin, scope_by_course

from . import grading, services
from .models import Attempt, Choice, Question, Quiz
from .parser import ParseError, parse

QUICK_HELP = _(
    "Har bir savol «?» bilan boshlanadi. «+» — to'g'ri, «-» — noto'g'ri variant (bir nechta «+» — "
    "bir nechta to'g'ri javob); «=» — matn javob; «1.», «2.» — to'g'ri tartib; «chap :: o'ng» — "
    "juft; «>» — izoh; ``` ichida — kod. Savollar mavjudlarining oxiriga qo'shiladi."
)
QUICK_EXAMPLE = """? HTML nimaning qisqartmasi?
+ HyperText Markup Language
- High Tech Modern Language
> HTML — sahifa tuzilmasi uchun belgilash tili.

? Moslang:
HTML :: tuzilma
CSS :: ko'rinish"""


class QuizInline(StackedInline):
    """Dars sahifasida: test sozlamalari; savollar — test sahifasida ("o'zgartirish" havolasi)."""

    model = Quiz
    extra = 0
    max_num = 1
    fields = ("title", ("pass_percent", "questions_per_attempt", "shuffle_questions"))
    show_change_link = True
    verbose_name = _("test")
    verbose_name_plural = _("test")


class QuestionInline(TabularInline):
    model = Question
    extra = 0
    fields = ("order", "kind", "text", "choices_link")
    readonly_fields = ("choices_link",)
    show_change_link = True
    ordering_field = "order"
    hide_ordering_field = True

    def get_queryset(self, request: HttpRequest) -> QuerySet[Question]:
        return super().get_queryset(request).annotate(choice_count=Count("choices"))

    def formfield_for_dbfield(self, db_field: Any, request: HttpRequest, **kwargs: Any) -> Any:
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == "text" and field is not None:
            field.widget = UnfoldAdminTextareaWidget(attrs={"rows": 2})
        return field

    @admin.display(description=_("Variantlar"))
    def choices_link(self, obj: Question) -> str:
        # Unfold "o'zgartirish" havolasini faqat sichqoncha ustida ko'rsatadi; bu — doim ko'rinadi.
        if obj.pk is None:
            return "—"
        count = getattr(obj, "choice_count", None)
        if count is None:
            count = obj.choices.count()
        return format_html(
            '<a href="{}" class="font-medium text-primary-600 whitespace-nowrap">{} ›</a>',
            reverse("admin:quizzes_question_change", args=[obj.pk]),
            _("%(count)s ta — o'zgartirish") % {"count": count},
        )


class QuizForm(forms.ModelForm):
    quick = forms.CharField(
        label=_("Tez kiritish"),
        required=False,
        widget=UnfoldAdminTextareaWidget(attrs={"rows": 12, "placeholder": QUICK_EXAMPLE}),
        help_text=QUICK_HELP,
    )

    class Meta:
        model = Quiz
        fields = ("lesson", "title", "pass_percent", "questions_per_attempt", "shuffle_questions")

    def clean_quick(self) -> list[Any]:
        source = self.cleaned_data.get("quick", "")
        if not source.strip():
            return []
        try:
            return parse(source)
        except ParseError as exc:
            raise ValidationError(exc.errors) from exc


@admin.register(Quiz)
class QuizAdmin(TeacherScopedAdmin, ModelAdmin):
    form = QuizForm
    teacher_course_path = "lesson__module__course"
    teacher_scoped_fields = {"lesson": "module__course"}
    list_display = ("title", "lesson", "show_questions", "show_attempts", "show_average")
    list_filter = ("lesson__module__course",)
    search_fields = ("title", "lesson__title")
    autocomplete_fields = ("lesson",)
    inlines = [QuestionInline]
    readonly_fields = ("stats",)
    fieldsets = (
        (None, {"fields": ("lesson", "title")}),
        (
            _("Sozlamalar"),
            {"fields": (("pass_percent", "questions_per_attempt", "shuffle_questions"),)},
        ),
        (_("Savollar qo'shish"), {"fields": ("quick",)}),
        (_("Natijalar"), {"fields": ("stats",)}),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Quiz]:
        return (
            super()
            .get_queryset(request)
            .select_related("lesson")
            .annotate(
                question_count=Count("questions", distinct=True),
                attempt_count=Count("attempts", distinct=True),
                average=Avg("attempts__score"),
            )
        )

    def save_related(self, request: HttpRequest, form: Any, formsets: Any, change: bool) -> None:
        super().save_related(request, form, formsets, change)
        drafts = form.cleaned_data.get("quick") or []
        if drafts:
            count = services.import_questions(form.instance, drafts)
            self.message_user(request, _("%(count)s ta savol qo'shildi.") % {"count": count})

    @display(description=_("Savollar"), ordering="question_count")
    def show_questions(self, obj: Quiz) -> int:
        return obj.question_count  # type: ignore[attr-defined, no-any-return]

    @display(description=_("Urinishlar"), ordering="attempt_count")
    def show_attempts(self, obj: Quiz) -> int:
        return obj.attempt_count  # type: ignore[attr-defined, no-any-return]

    @display(description=_("O'rtacha natija"), ordering="average")
    def show_average(self, obj: Quiz) -> str:
        average = obj.average  # type: ignore[attr-defined]
        return f"{round(average)}%" if average is not None else "—"

    @admin.display(description=_("Savollar bo'yicha"))
    def stats(self, obj: Quiz) -> str:
        if obj.pk is None:
            return "—"
        rows = [
            [
                row["question"].text[:90],
                row["answered"],
                "—" if row["percent"] is None else f"{row['percent']}%",
            ]
            for row in services.question_stats(obj)
        ]
        if not rows:
            return str(_("Hali savol yo'q."))
        # Unfold jadvali: admin'ning qolgan jadvallari bilan bir xil ko'rinish.
        return render_to_string(
            "unfold/components/table.html",
            {"table": {"headers": [_("Savol"), _("Javoblar"), _("To'g'ri")], "rows": rows}},
        )


class ChoiceFormSet(BaseInlineFormSet):
    """Savol turiga mos variantlar: masalan, bitta to'g'ri javobli savolda aynan bitta «to'g'ri»."""

    def clean(self) -> None:
        super().clean()
        kind = getattr(self.instance, "kind", None) or Question.Kind.SINGLE
        drafts = [
            grading.DraftChoice(
                text=form.cleaned_data.get("text", ""),
                is_correct=bool(form.cleaned_data.get("is_correct")),
                match=form.cleaned_data.get("match", ""),
            )
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE")
        ]
        problems = grading.problems(kind, drafts)
        if problems:
            raise ValidationError(problems)


class ChoiceInline(TabularInline):
    model = Choice
    formset = ChoiceFormSet
    extra = 0
    fields = ("order", "text", "is_correct", "match")
    ordering_field = "order"
    hide_ordering_field = True


@admin.register(Question)
class QuestionAdmin(TeacherScopedAdmin, ModelAdmin):
    teacher_course_path = "quiz__lesson__module__course"
    teacher_scoped_fields = {"quiz": "lesson__module__course"}
    list_display = ("text", "kind", "quiz")
    list_filter = ("kind", "quiz__lesson__module__course")
    search_fields = ("text",)
    autocomplete_fields = ("quiz",)
    inlines = [ChoiceInline]
    fieldsets = (
        (
            None,
            {
                "fields": ("quiz", "kind", "text"),
                "description": _(
                    "Variantlar: bitta yoki bir nechta to'g'ri javob — «to'g'ri» belgisi; matn "
                    "javob — har bir qabul qilinadigan yozuv alohida variant; tartiblash — "
                    "variantlar to'g'ri tartibda; moslashtirish — «juft» ustuniga o'ng tomon."
                ),
            },
        ),
        (_("Kod va izoh"), {"fields": (("code", "language"), "explanation")}),
    )

    def has_module_permission(self, request: HttpRequest) -> bool:
        # Menyuda alohida ko'rsatilmaydi: savollar test sahifasidan ochiladi.
        return False


@admin.register(Attempt)
class AttemptAdmin(ModelAdmin):
    """Test natijalari: faqat ko'rish."""

    list_display = ("student", "quiz", "show_score", "stars", "passed", "started_at", "finished_at")
    list_filter = ("passed", "quiz__lesson__module__course")
    search_fields = ("student__phone", "student__first_name", "student__last_name")
    list_select_related = ("student", "quiz", "quiz__lesson")
    date_hierarchy = "started_at"
    readonly_fields = ("student", "quiz", "started_at", "finished_at", "score", "stars", "passed")
    fields = readonly_fields

    def get_queryset(self, request: HttpRequest) -> QuerySet[Attempt]:
        queryset = super().get_queryset(request)
        return scope_by_course(queryset, request.user, "quiz__lesson__module__course")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    @display(description=_("Natija"), ordering="score")
    def show_score(self, obj: Attempt) -> str:
        return "—" if obj.score is None else f"{obj.score}%"
