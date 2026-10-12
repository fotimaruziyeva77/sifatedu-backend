"""Python — qayta imtihon (bir necha o'quvchi uchun): test oktabr imtihonining savollar bankidan,
amaliy topshiriqlar yangi. Guruhning qolganlariga ochilmaydi va xabar bormaydi.

O'quvchilar raqamini yozish shart emas: ularga havola yuboring —
  https://t.me/sifat_edubot?start=qayta
Botda shu havola orqali ro'yxatdan o'tganlar (telefon Telegram'dan olinadi) «qayta» manbasi bilan
yoziladi va skript ularni o'zi topadi.

Serverda, /srv/sifatedu papkasida (kod Django shell'ga uzatiladi, image qayta yig'ilmaydi):

  S=backend/scripts/imtihon_python_qayta.py
  dc exec -T -e ACTION=open -e SOURCE=qayta -e HOURS=3 backend python manage.py shell < $S
  dc exec -T -e ACTION=add -e SOURCE=qayta backend python manage.py shell < $S
  dc exec -T -e ACTION=add -e PHONES=+998901112233 backend python manage.py shell < $S
  dc exec -T -e ACTION=status backend python manage.py shell < $S

open   — bugungi qayta imtihonni yaratadi (bor bo'lsa — o'shani oladi): sozlamalar va savollar
         modullari oktabr imtihonidan, 4 ta yangi amaliy topshiriq. SOURCE havolasi orqali
         ro'yxatdan o'tganlar va PHONES dagilar Python guruhiga qo'shiladi (bo'lmasa), ularga
         hozirdan HOURS soat (standart 3) alohida muddat va botga xabar.
add    — keyin kelganlarni qo'shish: muddati avval qo'shilganlarniki bilan bir xil.
status — kim test ishladi, natija, nechta amaliy topshiriq yuborildi; bugun botga kirgan, lekin
         ro'yxatda yo'qlar (boshqa havola bilan kirgan bo'lsa — PHONES bilan qo'shing).

Imtihonning umumiy oynasi ochilgan zahoti yopiladi, shuning uchun uni faqat alohida muddat
berilganlar ishlaydi. Guruhning boshqalari saytdagi «Imtihonlar» sahifasida bu imtihonni
«Yopilgan» deb ko'rishi mumkin (botda ko'rinmaydi).

Baholash — saytda: «Guruhlarim» → «Oylik imtihonlar» → bugungi sanadagi Python imtihoni.
"""

import os
from datetime import date, datetime, timedelta

from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Course
from apps.exams.models import Exam, ExamAttempt, ExamExtension, ExamTask, TaskAnswer
from apps.learning.models import Enrollment, StudyGroup
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.users.models import User

ACTION = os.environ.get("ACTION", "status")
COURSE_SLUG = "python"
GROUP_NAME = "Python"
TEMPLATE_MONTH = date(2026, 10, 1)

TASKS = [
    (
        "1. Arifmetik amallar: do'kon",
        """Do'konda 1 kg olma 12500 so'm turadi. Xaridor 3 kg oldi va 50000 so'm berdi.
O'zgaruvchilar: narx = 12500, kg = 3, pul = 50000
Hisoblang va har birini alohida qatorda, izohi bilan chiqaring:
1) jami narx (narx * kg);
2) qaytim (pul - jami);
3) jami narxga 2000 so'mlik paket qo'shilgandagi summa (+);
4) 1 kg narxi ming so'mda (narx / 1000);
5) qaytimda nechta 5000 so'mlik bor (//);
6) 5000 so'mliklardan keyin qolgan qaytim (%);
7) kg ning 3-darajasi (**).

Kutilgan natija:
Jami: 37500
Qaytim: 12500
Paket bilan: 39500
1 kg (ming so'm): 12.5
5000 lik: 2
Qolgan: 2500
Daraja: 27

Kodni "Kod" maydoniga qo'ying.""",
    ),
    (
        "2. Matn bilan ishlash (string metodlari)",
        """O'zgaruvchi berilgan: matn = "  navoiy viloyati markazi  "
Quyidagilarni bajaring va har bir natijani chiqaring:
1) chetidagi bo'sh joylarni olib tashlang (strip);
2) har so'zni bosh harf bilan chiqaring (title);
3) matnda "i" harfi necha marta uchrashini chiqaring (count);
4) "markazi" so'zini "shahri" so'ziga almashtiring (replace);
5) matnni so'zlarga ajrating (split) va so'zlar sonini chiqaring (len);
6) "viloyati" so'zi qaysi o'rindan boshlanishini chiqaring (find).
2–6-bandlarni 1-banddagi tozalangan matn bilan bajaring.

Kutilgan natija:
navoiy viloyati markazi
Navoiy Viloyati Markazi
4
navoiy viloyati shahri
3
7""",
    ),
    (
        "3. Math metodlari",
        """math modulini ulang (import math) va hisoblab chiqaring:
1) 196 ning kvadrat ildizi (sqrt);
2) 4.2 ni yuqoriga va 4.8 ni pastga yaxlitlash (ceil, floor);
3) 84 va 60 ning EKUBi (gcd);
4) 1000 ning 10 asosli logarifmi (log10);
5) 3.14159 ni verguldan keyin 3 xonagacha yaxlitlash (round);
6) 5 ning faktoriali (factorial) va -42 ning musbat qiymati (abs).

Kutilgan natija:
14.0
5 4
12
3.0
3.142
120 42""",
    ),
    (
        "4. Shartli operatorlar: ob-havo",
        """harorat o'zgaruvchisi berilgan (masalan, harorat = 24).
Maslahat chiqaradigan dastur yozing:
-50 dan -11 gacha → "Juda sovuq — uyda qoling"
-10 dan 0 gacha → "Sovuq — issiq kiyining"
1 dan 15 gacha → "Salqin — kurtka oling"
16 dan 30 gacha → "Iliq — sayrga chiqing"
31 dan 60 gacha → "Issiq — ko'p suv iching"
-50 dan kichik yoki 60 dan katta → "Noto'g'ri qiymat"
if / elif / else va mantiqiy operatorlardan (and, or) foydalaning. Harorat to'g'ri bo'lsa, uning
juft yoki toqligini ham chiqaring (% operatori bilan).

Tekshirish:
harorat = 24 → Iliq — sayrga chiqing, Juft
harorat = -7 → Sovuq — issiq kiyining, Toq
harorat = 75 → Noto'g'ri qiymat""",
    ),
]


def course() -> Course:
    found = Course.objects.filter(slug=COURSE_SLUG).first()
    if found is None:
        raise SystemExit("Python kursi topilmadi.")
    return found


def admin() -> User | None:
    return User.objects.filter(is_active=True, is_superuser=True).order_by("date_joined").first()


def retake() -> Exam | None:
    """Bugungi qayta imtihon (oy sanasi — ochilgan kun; oyning 1-kuni — oddiy oylik imtihon)."""
    today = timezone.localdate()
    if today.day == 1:
        raise SystemExit("Oyning 1-kuni qayta imtihon ochilmaydi: bu sana oylik imtihonniki.")
    return Exam.objects.filter(course=course(), month=today).first()


def name_of(user: User) -> str:
    return f"{user.first_name} {user.last_name}".strip() or "(ismsiz)"


def students() -> list[User]:
    """SOURCE havolasi orqali botda ro'yxatdan o'tganlar va PHONES dagilar."""
    numbers = []
    for raw in os.environ.get("PHONES", "").split(","):
        digits = "".join(char for char in raw if char.isdigit())
        if digits:
            numbers.append("+" + (digits if digits.startswith("998") else "998" + digits))
    source = os.environ.get("SOURCE", "").strip()
    if not numbers and not source:
        raise SystemExit("Kim uchun? -e SOURCE=qayta yoki -e PHONES=+998901234567,+998931112233")
    people: dict[int, User] = {}
    if source:
        joined = User.objects.filter(signup_source=source, is_active=True, is_staff=False)
        people.update((user.pk, user) for user in joined.order_by("date_joined"))
        if not people:
            print(f"  ! «{source}» havolasi orqali hali hech kim ro'yxatdan o'tmagan")
    found = {user.phone: user for user in User.objects.filter(phone__in=numbers, is_active=True)}
    for number in numbers:
        if number in found:
            people[found[number].pk] = found[number]
        else:
            print(f"  ! {number} — bunday o'quvchi topilmadi (botda ro'yxatdan o'tganmi?)")
    return list(people.values())


def enroll(user: User) -> str:
    """Python guruhida (faol) bo'lmasa — qo'shadi. Qaytadi: chop etish uchun izoh."""
    python = course()
    if Enrollment.objects.filter(
        user=user, course=python, status=Enrollment.Status.ACTIVE
    ).exists():
        return ""
    Enrollment.objects.update_or_create(
        user=user,
        course=python,
        defaults={
            "status": Enrollment.Status.ACTIVE,
            "group": StudyGroup.objects.filter(course=python, name=GROUP_NAME).first(),
            "source": Enrollment.Source.MANUAL,
            "study_format": Enrollment.Format.OFFLINE,
        },
    )
    return ", Python guruhiga qo'shildi"


@transaction.atomic
def create(now: datetime) -> Exam:
    template = Exam.objects.filter(course=course(), month=TEMPLATE_MONTH).first()
    if template is None:
        raise SystemExit("Oktabr imtihoni topilmadi — sozlamalar undan olinadi.")
    exam = Exam.objects.create(
        course=template.course,
        month=timezone.localdate(),
        status=Exam.Status.READY,
        questions_count=template.questions_count,
        duration_min=template.duration_min,
        pass_percent=template.pass_percent,
        test_weight=template.test_weight,
        # Umumiy oyna darhol yopiladi: imtihonni faqat alohida muddat berilganlar ishlaydi,
        # guruhning qolganlariga «imtihon ochildi» xabari ham bormaydi.
        opens_at=now,
        closes_at=now,
        opened_notified_at=now,
        created_by=admin(),
    )
    exam.modules.set(template.modules.all())
    for order, (title, instructions) in enumerate(TASKS, 1):
        ExamTask.objects.create(exam=exam, order=order, title=title, instructions=instructions)
    return exam


def grant(exam: Exam, people: list[User], until: datetime) -> None:
    by = admin()
    finish = timezone.localtime(until)
    for user in people:
        joined = enroll(user)
        ExamExtension.objects.update_or_create(
            exam=exam, student=user, defaults={"until": until, "granted_by": by}
        )
        sent = notify(
            user,
            Notification.Kind.EXAM_OPENED,
            title="Qayta imtihon ochildi: Python",
            body=(
                f"Test — {exam.questions_count} ta savol, {exam.duration_min} daqiqa, bitta "
                f"urinish; amaliy topshiriqlar — {exam.tasks.count()} ta (yangi). "
                f"{finish:%H:%M} gacha topshiring: saytda yoki botdagi «📝 Testlar» bo'limida."
            ),
            link=f"/dashboard/exams/{exam.pk}",
            dedupe_key=f"exam-retake:{exam.pk}:{user.pk}",
        )
        note = "xabar yuborildi" if sent is not None else "xabar avval yuborilgan"
        print(f"  + {name_of(user)} ({user.phone}) — {finish:%d.%m %H:%M} gacha, {note}{joined}")


def deadline(exam: Exam, now: datetime) -> datetime:
    """Avval berilgan muddat (hali o'tmagan bo'lsa) — qayta ishga tushirsa ham siljimaydi;
    bo'lmasa hozirdan HOURS soat."""
    latest = exam.extensions.order_by("-until").first()
    if latest is not None and latest.until > now:
        return latest.until
    return now + timedelta(hours=float(os.environ.get("HOURS", "3")))


def open_retake() -> None:
    people = students()
    if not people:
        raise SystemExit("Hech kim topilmadi.")
    now = timezone.now()
    exam = retake() or create(now)
    print(
        f"Qayta imtihon: id {exam.pk}, {exam.questions_count} savol, "
        f"{exam.duration_min} daqiqa, amaliy — {exam.tasks.count()} ta"
    )
    grant(exam, people, deadline(exam, now))


def add() -> None:
    exam = retake()
    if exam is None:
        raise SystemExit("Bugun qayta imtihon ochilmagan: avval ACTION=open.")
    grant(exam, students(), deadline(exam, timezone.now()))


def status() -> None:
    exam = retake()
    if exam is None:
        print("Bugun qayta imtihon ochilmagan.")
        return
    tasks = exam.tasks.count()
    print(f"Qayta imtihon (id {exam.pk}):")
    for extension in exam.extensions.select_related("student").order_by("student__first_name"):
        user = extension.student
        attempt = ExamAttempt.objects.filter(exam=exam, student=user).first()
        if attempt is None:
            test = "boshlamagan"
        elif attempt.finished_at is None:
            test = "ishlayapti"
        else:
            test = f"{attempt.score}%"
        sent = TaskAnswer.objects.filter(task__exam=exam, student=user).count()
        until = timezone.localtime(extension.until)
        print(f"  {name_of(user)[:26]:26} {test:12} amaliy {sent}/{tasks}  ({until:%H:%M} gacha)")
    listed = set(exam.extensions.values_list("student_id", flat=True))
    today = User.objects.filter(
        date_joined__date=timezone.localdate(), is_staff=False, is_active=True
    ).exclude(pk__in=listed)
    if today:
        print("Bugun botga kirgan, lekin ro'yxatda yo'q (kerak bo'lsa — ACTION=add, PHONES=...):")
        for user in today.order_by("date_joined"):
            print(f"  {name_of(user)[:26]:26} {user.phone}  manba: {user.signup_source or '—'}")


ACTIONS = {"open": open_retake, "add": add, "status": status}
if ACTION not in ACTIONS:
    raise SystemExit(f"ACTION: {', '.join(ACTIONS)}")
ACTIONS[ACTION]()
