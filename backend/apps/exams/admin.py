"""Admin: oylik imtihonni tayyorlash (modullar, 5 ta amaliy topshiriq, sozlamalar) va natijalar."""

from typing import Any

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Q, QuerySet
from django.http import HttpRequest
from django.utils.html import format_html_join
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, StackedInline
from unfold.decorators import display

from apps.catalog.models import Module
from apps.catalog.scope import TeacherScopedAdmin

from . import services
from .models import MAX_TASKS, Exam, ExamResult, ExamTask


class ExamTaskInline(StackedInline):
    model = ExamTask
    extra = 0
    max_num = MAX_TASKS
    fields = (("order", "title"), "instructions")
    verbose_name_plural = _("amaliy topshiriqlar (5 ta)")


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = (
            "course",
            "month",
            "status",
            "modules",
            "questions_count",
            "duration_min",
            "pass_percent",
            "test_weight",
            "opens_at",
            "closes_at",
        )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for name in ("opens_at", "closes_at"):
            self.fields[name].required = False
            self.fields[name].help_text = _("Bo'sh — oyning 25-kunidan oy oxirigacha.")
        course_id = self.instance.course_id if self.instance.pk else None
        modules = self.fields["modules"]
        modules.queryset = (  # type: ignore[attr-defined]
            Module.objects.filter(course_id=course_id).order_by("order", "id")
            if course_id
            else Module.objects.none()
        )
        if not course_id:
            modules.help_text = _("Kursni tanlab saqlang — keyin uning modullari chiqadi.")

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        month = cleaned.get("month")
        if month:
            cleaned["month"] = services.month_start(month)
            opens, closes = services.window(cleaned["month"])
            cleaned["opens_at"] = cleaned.get("opens_at") or opens
            cleaned["closes_at"] = cleaned.get("closes_at") or closes
        if (
            cleaned.get("opens_at")
            and cleaned.get("closes_at")
            and cleaned["opens_at"] >= cleaned["closes_at"]
        ):
            raise ValidationError({"closes_at": _("Yopilish vaqti ochilishdan keyin bo'lsin.")})
        course = cleaned.get("course")
        chosen = cleaned.get("modules")
        if course and chosen and any(item.course_id != course.pk for item in chosen):
            raise ValidationError({"modules": _("Modullar shu kursniki bo'lsin.")})
        return cleaned


@admin.register(Exam)
class ExamAdmin(TeacherScopedAdmin, ModelAdmin):
    form = ExamForm
    teacher_course_path = "course"
    teacher_scoped_fields = {"course": "pk"}
    list_display = (
        "__str__",
        "show_status",
        "opens_at",
        "closes_at",
        "show_tasks",
        "show_results",
    )
    list_filter = ("status", "course")
    search_fields = ("course__title",)
    list_select_related = ("course",)
    filter_horizontal = ("modules",)
    inlines = [ExamTaskInline]
    readonly_fields = ("results_table",)
    fieldsets = (
        (
            None,
            {
                "fields": ("course", "month", "status"),
                "description": _(
                    "Har oyning 20-kuni qoralama o'zi yaratiladi. 5 ta amaliy topshiriqni yozing, "
                    "savollar modullarini tanlang va «Tayyor» qiling — tayyor bo'lmagan imtihon "
                    "ochilmaydi. Baholash — o'qituvchi kabinetida."
                ),
            },
        ),
        (
            _("Test qismi"),
            {
                "fields": (
                    "modules",
                    ("questions_count", "duration_min"),
                    ("pass_percent", "test_weight"),
                )
            },
        ),
        (_("Vaqt"), {"fields": (("opens_at", "closes_at"),)}),
        (_("Natijalar"), {"fields": ("results_table",)}),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Exam]:
        return (
            super()
            .get_queryset(request)
            .annotate(
                task_count=Count("tasks", distinct=True),
                result_count=Count("results", distinct=True),
                passed_count=Count("results", filter=Q(results__passed=True), distinct=True),
            )
        )

    def get_fieldsets(self, request: HttpRequest, obj: Any = None) -> Any:
        return self.fieldsets if obj is not None else self.fieldsets[:-1]

    def save_model(self, request: HttpRequest, obj: Exam, form: Any, change: bool) -> None:
        if not change:
            obj.created_by = request.user  # type: ignore[assignment]
        super().save_model(request, obj, form, change)

    def save_related(self, request: HttpRequest, form: Any, formsets: Any, change: bool) -> None:
        super().save_related(request, form, formsets, change)
        exam = form.instance
        if exam.status != Exam.Status.READY:
            return
        problems = []
        if not exam.tasks.exists():
            problems.append(str(_("amaliy topshiriq yo'q")))
        if not services.question_pool(exam):
            problems.append(str(_("tanlangan modullarda test savoli yo'q")))
        if problems:
            Exam.objects.filter(pk=exam.pk).update(status=Exam.Status.DRAFT)
            messages.warning(
                request,
                _("Imtihon qoralamada qoldi: %(problems)s.") % {"problems": ", ".join(problems)},
            )

    @display(
        description=_("Holat"),
        label={Exam.Status.DRAFT: "warning", Exam.Status.READY: "success"},
    )
    def show_status(self, obj: Exam) -> tuple[str, str]:
        return obj.status, obj.get_status_display()

    @admin.display(description=_("Topshiriqlar"))
    def show_tasks(self, obj: Exam) -> str:
        return f"{obj.task_count}/{MAX_TASKS}"  # type: ignore[attr-defined]

    @admin.display(description=_("Natijalar (o'tdi)"))
    def show_results(self, obj: Exam) -> str:
        return f"{obj.result_count} ({obj.passed_count})"  # type: ignore[attr-defined]

    @admin.display(description=_("Natijalar"))
    def results_table(self, obj: Exam) -> str:
        rows = obj.results.select_related("student").order_by("-total")[:200]
        if not rows:
            return str(_("Hali natija yo'q."))
        return format_html_join(
            "",
            "<div>{} — {}% ({}{})</div>",
            (
                (
                    row.student.get_full_name() or row.student.phone,
                    row.total,
                    _("o'tdi") if row.passed else _("o'tmadi"),
                    "" if row.final_at else ", " + str(_("yakuniy emas")),
                )
                for row in rows
            ),
        )


@admin.register(ExamResult)
class ExamResultAdmin(TeacherScopedAdmin, ModelAdmin):
    """Natijalar ro'yxati (faqat ko'rish): baholash o'qituvchi kabinetida."""

    teacher_course_path = "exam__course"
    list_display = (
        "student",
        "exam",
        "test_score",
        "practical_score",
        "total",
        "passed",
        "final_at",
    )
    list_filter = ("passed", "exam__course")
    search_fields = ("student__phone", "student__first_name", "student__last_name")
    list_select_related = ("student", "exam__course")
    readonly_fields = list_display

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False
