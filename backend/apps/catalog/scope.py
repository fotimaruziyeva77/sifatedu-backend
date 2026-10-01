"""O'qituvchi admin'da faqat o'z kurslarini ko'radi (TZ 3.2).

"O'z kursi" — kurs sahifasida ustoz sifatida biriktirilgan (`Course.instructors`), ustoz profili
esa foydalanuvchi akkauntiga bog'langan (`Instructor.user`). Admin, Menejer va Direktor hammasini
ko'radi.
"""

from typing import Any

from django.db.models import Model, Q, QuerySet
from django.http import HttpRequest

from apps.users.roles import sees_all

from .models import Course, Lesson


def teacher_courses(user: Any) -> QuerySet[Course]:
    return Course.objects.filter(instructors__user=user)


def scope_by_course[M: Model](queryset: QuerySet[M], user: Any, course_path: str) -> QuerySet[M]:
    """`course_path` — modeldan kursgacha yo'l: "pk" (kursning o'zi), "course", "module__course"."""
    if sees_all(user):
        return queryset
    return queryset.filter(**{f"{course_path}__in": teacher_courses(user).values("pk")})


def scope_videos[M: Model](queryset: QuerySet[M], user: Any) -> QuerySet[M]:
    """O'qituvchiga: o'zi yuklagan videolar va o'z kurslari darslaridagi videolar."""
    if sees_all(user):
        return queryset
    lessons = Lesson.objects.filter(module__course__in=teacher_courses(user).values("pk"))
    return queryset.filter(Q(uploaded_by=user) | Q(pk__in=lessons.values("video_id")))


class TeacherScopedAdmin:
    """ModelAdmin uchun: ro'yxat va sahifalar o'qituvchining kurslari bilan cheklanadi.

    Tanlov maydonlari (masalan, darsning moduli) ham cheklanadi — aks holda boshqa kursning
    ID'sini qo'lda yuborib, unga dars qo'shish mumkin bo'lardi.
    """

    teacher_course_path = "course"
    # Maydon nomi → shu maydon tanlovlari uchun modeldan kursgacha yo'l.
    teacher_scoped_fields: dict[str, str] = {}

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        queryset = super().get_queryset(request)  # type: ignore[misc]
        return scope_by_course(queryset, request.user, self.teacher_course_path)

    def formfield_for_foreignkey(self, db_field: Any, request: HttpRequest, **kwargs: Any) -> Any:
        path = self.teacher_scoped_fields.get(db_field.name)
        if path is not None:
            queryset = kwargs.get("queryset")
            if queryset is None:
                queryset = db_field.remote_field.model._default_manager.all()
            kwargs["queryset"] = scope_by_course(queryset, request.user, path)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)  # type: ignore[misc]
