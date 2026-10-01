"""Ommaviy katalog: kategoriyalar, kurslar ro'yxati va kurs sahifasi."""

from django.db.models import Count, Prefetch, Q, QuerySet
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny

from .filters import CourseFilter
from .models import Category, Course, Instructor, Lesson, Module
from .serializers import CategorySerializer, CourseCardSerializer, CourseDetailSerializer

LANGUAGE_HEADER = OpenApiParameter(
    name="Accept-Language",
    location=OpenApiParameter.HEADER,
    description="uz, ru yoki en",
    required=False,
)


def published_courses() -> QuerySet[Course]:
    return Course.objects.filter(status=Course.Status.PUBLISHED)


@extend_schema(parameters=[LANGUAGE_HEADER], tags=["catalog"])
class CategoryListView(ListAPIView[Category]):
    # Ommaviy: so'rovlar Next.js serveridan keladi (bitta IP), shuning uchun throttle yo'q.
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []
    serializer_class = CategorySerializer
    pagination_class = None
    filter_backends: list[type] = []

    def get_queryset(self) -> QuerySet[Category]:
        # Bo'sh kategoriya filtrlarda ko'rinmaydi.
        return (
            Category.objects.annotate(
                course_count=Count("courses", filter=Q(courses__status=Course.Status.PUBLISHED))
            )
            .filter(course_count__gt=0)
            .order_by("order", "id")
        )


@extend_schema(parameters=[LANGUAGE_HEADER], tags=["catalog"])
class CourseListView(ListAPIView[Course]):
    # Ommaviy: so'rovlar Next.js serveridan keladi (bitta IP), shuning uchun throttle yo'q.
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []
    serializer_class = CourseCardSerializer
    filterset_class = CourseFilter

    def get_queryset(self) -> QuerySet[Course]:
        return (
            published_courses()
            .select_related("category")
            .prefetch_related(
                Prefetch("instructors", queryset=Instructor.objects.filter(is_published=True))
            )
        )


@extend_schema(parameters=[LANGUAGE_HEADER], tags=["catalog"])
class CourseDetailView(RetrieveAPIView[Course]):
    # Ommaviy: so'rovlar Next.js serveridan keladi (bitta IP), shuning uchun throttle yo'q.
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []
    serializer_class = CourseDetailSerializer
    lookup_field = "slug"
    filter_backends: list[type] = []

    def get_queryset(self) -> QuerySet[Course]:
        lessons = Lesson.objects.order_by("order", "id")
        return (
            published_courses()
            .select_related("category")
            .prefetch_related(
                Prefetch("instructors", queryset=Instructor.objects.filter(is_published=True)),
                Prefetch(
                    "modules",
                    queryset=Module.objects.order_by("order", "id").prefetch_related(
                        Prefetch("lessons", queryset=lessons)
                    ),
                ),
            )
        )
