"""E2E testlar uchun ma'lumot: har ishga tushishda bir xil holat.

Faqat DEBUG rejimida ishlaydi — production bazasida test akkaunti yaratilmasligi uchun.
Parol `E2E_USER_PASSWORD` dan olinadi (standart qiymat — faqat local va CI uchun).
"""

import os
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Course, Instructor, Lesson
from apps.certificates.models import Certificate
from apps.exams.models import Exam, ExamTask
from apps.exams.services import month_start
from apps.homework.models import Assignment, Submission
from apps.learning.models import Enrollment, LessonProgress, StudyGroup
from apps.live.models import GroupLesson, LiveLesson
from apps.notifications.models import Notification
from apps.payments.models import Order, PaymentLog, PaymentTransaction, Refund
from apps.quizzes.models import Attempt, Quiz
from apps.quizzes.parser import parse
from apps.quizzes.services import import_questions
from apps.rewards import services as rewards
from apps.rewards.models import Coupon, DailyTask, Entry, ReviewAttempt, Wallet
from apps.shop.models import Product, Purchase
from apps.users.models import User
from apps.users.roles import Role, set_roles

E2E_PHONE = "+998900009999"
E2E_TEACHER_PHONE = "+998900008888"
# Onlayn o'quvchi (guruhsiz): keyingi dars oldingi darsning testidan o'tilgach ochiladi.
E2E_ONLINE_PHONE = "+998900007777"
# Faqat local va CI test akkauntlari uchun: buyruq DEBUG bo'lmasa ishlamaydi.
DEFAULT_PASSWORD = "E2e-sinov-parol-2026"  # noqa: S105
DEFAULT_TEACHER_PASSWORD = "E2e-ustoz-parol-2026"  # noqa: S105
DEFAULT_ONLINE_PASSWORD = "E2e-onlayn-parol-2026"  # noqa: S105
# To'lov testi shu kursni sotib oladi: boshida unga kirish bo'lmasligi kerak.
PURCHASE_COURSE = "praktikum-backend"
# O'qituvchi testi: test o'quvchisi shu kurs guruhida.
GROUP_COURSE = "frontend"
GROUP_NAME = "E2E-FE"
# Xabarlar testi: kabinetdagi bitta o'qilmagan xabar (Telegram va SMS'siz).
NOTICE_TITLE = "E2E: ertaga dars 19:00 da"
# Jonli darslar testi: 10 daqiqadan keyin boshlanadigan onlayn dars va kechagi dars.
LIVE_TITLE = "E2E: jonli dars"
LIVE_PAST_TITLE = "E2E: o'tgan dars"
LIVE_MEET = "https://meet.google.com/e2e-sinov-dars"
# Uy vazifasi testi: guruh kursining birinchi darsida.
HOMEWORK_TITLE = "E2E: shaxsiy sahifa"
# Oylik imtihon testi: guruh kursida ochiq imtihon (savollar — dars testidan, aralash tartibda)
# va 2 ta amaliy topshiriq. Sertifikat — tekshirish sahifasi uchun (raqami doimiy).
EXAM_TASKS = ("E2E: portfolio sahifasi", "E2E: CSS kartochka")
CERTIFICATE_NUMBER = "SE-2601-E2ESNV"
# Test o'yini: o'sha darsda, 5 turdagi savol, aralashtirilmaydi (E2E tartibni biladi).
QUIZ_TITLE = "E2E: HTML asoslari"
QUIZ_QUESTIONS = """
? HTML nimaning qisqartmasi?
+ HyperText Markup Language
- High Tech Modern Language
- Hyper Tool Multi Language
> HTML — sahifa tuzilmasi uchun belgilash tili.

? Qaysilari HTML teglari?
+ <div>
+ <p>
- <color>
> <color> degan teg yo'q: rang CSS bilan beriladi.

? Eng katta sarlavha tegi qaysi? Faqat nomini yozing.
= h1
= <h1>

? Brauzer sahifani qanday tayyorlaydi? Tartibga qo'ying.
1. HTML o'qiladi
2. CSS qo'llanadi
3. JavaScript ishga tushadi

? Moslang:
HTML :: tuzilma
CSS :: ko'rinish
JavaScript :: harakat
"""


class Command(BaseCommand):
    help = "E2E testlar uchun katalog va test o'quvchisini tayyorlaydi (faqat DEBUG)."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG:
            raise CommandError("seed_e2e faqat DEBUG rejimida ishlaydi.")

        call_command("seed_demo", verbosity=0)

        user, _created = User.objects.get_or_create(
            phone=E2E_PHONE, defaults={"first_name": "Sinov", "audience": User.Audience.ADULT}
        )
        user.first_name = "Sinov"
        user.audience = User.Audience.ADULT
        user.is_active = True
        user.marketing_consent_at = None
        user.set_password(os.environ.get("E2E_USER_PASSWORD", DEFAULT_PASSWORD))
        user.save()

        # Oldingi ishga tushishdan qolgan buyurtma va kirishlar tozalanadi.
        orders = Order.objects.filter(user=user)
        PaymentLog.objects.filter(order__in=orders).delete()
        Refund.objects.filter(order__in=orders).delete()
        PaymentTransaction.objects.filter(order__in=orders).delete()
        orders.delete()
        Enrollment.objects.filter(user=user).delete()
        LessonProgress.objects.filter(user=user).delete()
        Submission.objects.filter(student=user).delete()
        Attempt.objects.filter(student=user).delete()
        Notification.objects.filter(user=user).delete()
        Notification.objects.create(
            user=user,
            kind=Notification.Kind.BROADCAST,
            title=NOTICE_TITLE,
            body="Guruh darsi bir soat kechroq boshlanadi.\nXona o'sha-o'sha.",
            link="/dashboard/courses",
        )

        self.seed_teacher(user)
        self.seed_online()
        self.seed_exam(user)
        self.seed_rewards(user)
        self.seed_shop(user)

        course = Course.objects.get(slug=PURCHASE_COURSE)
        course.status = Course.Status.PUBLISHED
        course.is_free = False
        course.study_format = Course.Format.BOTH
        course.price_online = course.price_online or 1_400_000
        course.price_offline_monthly = course.price_offline_monthly or 600_000
        course.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"E2E tayyor: {E2E_PHONE}, kurs: {PURCHASE_COURSE}; ustoz: {E2E_TEACHER_PHONE}"
            )
        )

    def seed_exam(self, student: User) -> None:
        """Guruh kursida ochiq oylik imtihon (5 savol, 30 daqiqa) va o'quvchining sertifikati."""
        course = Course.objects.get(slug=GROUP_COURSE)
        Exam.objects.filter(course=course).delete()
        now = timezone.now().replace(second=0, microsecond=0)
        exam = Exam.objects.create(
            course=course,
            month=month_start(timezone.localdate()),
            status=Exam.Status.READY,
            questions_count=5,
            duration_min=30,
            opens_at=now - timedelta(hours=1),
            closes_at=now + timedelta(days=3),
            # Ochilish xabari yuborilgan deb belgilanadi: E2E'da ortiqcha xabar chiqmasin.
            opened_notified_at=now,
        )
        for order, title in enumerate(EXAM_TASKS, 1):
            ExamTask.objects.create(
                exam=exam,
                order=order,
                title=title,
                instructions="Sahifani yasang va GitHub havolasini yoki faylni yuboring.",
            )
        Certificate.objects.filter(user=student).delete()
        Certificate.objects.create(
            user=student,
            course=course,
            number=CERTIFICATE_NUMBER,
            full_name="Sinov O'quvchi",
            score=92,
        )

    def seed_rewards(self, student: User) -> None:
        """XP va coin: o'quvchida mukofotlar va bitta shtraf (o'qituvchi bekor qiladi), bugungi
        topshiriqlar; onlayn o'quvchi reytingda birinchi va ustoz taklifi bilan kelgan (birinchi
        to'lovga chegirma)."""
        online = User.objects.get(phone=E2E_ONLINE_PHONE)
        teacher = User.objects.get(phone=E2E_TEACHER_PHONE)
        people = [student, online, teacher]
        for model in (Entry, Wallet, DailyTask, Coupon, ReviewAttempt):
            model.objects.filter(user__in=people).delete()
        course = Course.objects.get(slug=GROUP_COURSE)
        first = (
            Lesson.objects.filter(module__course=course)
            .order_by("module__order", "module__id", "order", "id")
            .first()
        )
        rewards.reward(student.pk, Entry.Reason.LESSON, 10, key="e2e:lesson", course_id=course.pk)
        rewards.reward(student.pk, Entry.Reason.QUIZ, 15, key="e2e:quiz", course_id=course.pk)
        rewards.penalize(
            student.pk, Entry.Reason.LATE, 5, key="e2e:late", course_id=course.pk, note=LIVE_TITLE
        )
        rewards.reward(online.pk, Entry.Reason.LESSON, 30, key="e2e:online", course_id=course.pk)
        DailyTask.objects.create(
            user=student,
            kind=DailyTask.Kind.LESSON,
            course=course,
            lesson=first,
            title=str(first.title) if first else "",
        )
        DailyTask.objects.create(user=student, kind=DailyTask.Kind.REVIEW)
        online.referred_by = teacher
        online.save(update_fields=["referred_by"])

    def seed_shop(self, student: User) -> None:
        """Do'kon: arzon sovg'a (o'quvchining coini yetadi) va qimmati (yetmaydi)."""
        Purchase.objects.filter(user=student).delete()
        Product.objects.filter(name_uz__startswith="E2E:").delete()
        Product.objects.create(
            name_uz="E2E: stikerlar to'plami",
            description_uz="Sifat Edu stikerlari — noutbuk uchun.",
            price=20,
            stock=5,
            kind=Product.Kind.PHYSICAL,
            order=1,
        )
        Product.objects.create(
            name_uz="E2E: futbolka",
            description_uz="Sifat Edu futbolkasi.",
            price=500,
            kind=Product.Kind.PHYSICAL,
            order=2,
        )

    def seed_online(self) -> None:
        """Onlayn o'quvchi guruh kursida: birinchi darsning testi hali o'tilmagan."""
        user, _created = User.objects.get_or_create(
            phone=E2E_ONLINE_PHONE, defaults={"first_name": "Onlayn"}
        )
        user.first_name, user.is_active = "Onlayn", True
        user.set_password(os.environ.get("E2E_ONLINE_PASSWORD", DEFAULT_ONLINE_PASSWORD))
        user.save()
        Attempt.objects.filter(student=user).delete()
        LessonProgress.objects.filter(user=user).delete()
        Enrollment.objects.update_or_create(
            user=user,
            course=Course.objects.get(slug=GROUP_COURSE),
            defaults={
                "status": Enrollment.Status.ACTIVE,
                "source": Enrollment.Source.MANUAL,
                "study_format": Enrollment.Format.ONLINE,
                "group": None,
                "expires_at": None,
            },
        )

    def seed_teacher(self, student: User) -> None:
        """Ustoz, uning kursi (admin'da faqat shu kurs ko'rinadi) va test o'quvchili guruhi."""
        teacher, _created = User.objects.get_or_create(
            phone=E2E_TEACHER_PHONE, defaults={"first_name": "Ustoz", "last_name": "Sinov"}
        )
        teacher.first_name, teacher.last_name, teacher.is_active = "Ustoz", "Sinov", True
        teacher.set_password(os.environ.get("E2E_TEACHER_PASSWORD", DEFAULT_TEACHER_PASSWORD))
        teacher.save()
        set_roles(teacher, [Role.TEACHER])

        course = Course.objects.get(slug=GROUP_COURSE)
        profile, _created = Instructor.objects.get_or_create(
            user=teacher, defaults={"slug": "e2e-ustoz", "full_name": "Ustoz Sinov"}
        )
        course.instructors.add(profile)

        group, _created = StudyGroup.objects.update_or_create(
            course=course,
            name=GROUP_NAME,
            defaults={
                "teacher": teacher,
                "study_format": Enrollment.Format.OFFLINE,
                "schedule": "Du, Chor, Ju — 18:00",
                "status": StudyGroup.Status.ACTIVE,
            },
        )
        Enrollment.objects.create(
            user=student,
            course=course,
            source=Enrollment.Source.MANUAL,
            study_format=Enrollment.Format.OFFLINE,
            group=group,
        )
        first = (
            Lesson.objects.filter(module__course=course)
            .order_by("module__order", "module__id", "order", "id")
            .first()
        )
        if first is not None:
            Assignment.objects.update_or_create(
                lesson=first,
                defaults={
                    "title": HOMEWORK_TITLE,
                    "instructions": "Ismingiz yozilgan HTML sahifa yasang va kodini yuboring.",
                    "deadline": None,
                },
            )
            quiz, _created = Quiz.objects.update_or_create(
                lesson=first,
                defaults={
                    "title": QUIZ_TITLE,
                    "pass_percent": 70,
                    "questions_per_attempt": 0,
                    "shuffle_questions": False,
                },
            )
            quiz.questions.all().delete()
            import_questions(quiz, parse(QUIZ_QUESTIONS))

        # Offlayn guruh: birinchi dars "o'tilgan" — uning uy vazifasi va testi o'quvchiga ochiq.
        group.covered_lessons.all().delete()
        if first is not None:
            GroupLesson.objects.create(group=group, lesson=first)

        # Jonli darslar: "Qo'shilish" hozir ochiq bo'lgan dars va kechagi dars (yozuv, izoh bilan).
        group.live_lessons.all().delete()
        now = timezone.now().replace(second=0, microsecond=0)
        LiveLesson.objects.create(
            group=group,
            starts_at=now + timedelta(minutes=10),
            # Uzun dars: sekin mashinada ham butun E2E davomida "Qo'shilish" ochiq turadi.
            duration_min=240,
            kind=LiveLesson.Kind.ONLINE,
            meet_url=LIVE_MEET,
            title=LIVE_TITLE,
        )
        LiveLesson.objects.create(
            group=group,
            starts_at=now - timedelta(days=1),
            kind=LiveLesson.Kind.ONLINE,
            meet_url=LIVE_MEET,
            title=LIVE_PAST_TITLE,
            notes="Flexbox va Grid: kartochkalarni joylashtirish.",
            recording_url="https://youtu.be/e2e-sinov",
        )
