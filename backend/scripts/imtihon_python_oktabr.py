"""Python guruhi — oktabr oylik imtihoni: savollar banki, amaliy topshiriqlar, guruh va ochish.

Serverda, /srv/sifatedu papkasida (kod Django shell'ga uzatiladi, image qayta yig'ilmaydi):

  S=backend/scripts/imtihon_python_oktabr.py
  dc exec -T -e ACTION=setup    backend python manage.py shell < $S
  dc exec -T -e ACTION=students backend python manage.py shell < $S
  dc exec -T -e ACTION=enroll   backend python manage.py shell < $S
  dc exec -T -e ACTION=open     backend python manage.py shell < $S
  dc exec -T -e ACTION=status   backend python manage.py shell < $S
  dc exec -T -e ACTION=close    backend python manage.py shell < $S
  dc exec -T -e ACTION=remove -e PHONES=+998901234567 backend python manage.py shell < $S

setup    — kurs, savollar banki (32 ta, har o'quvchiga tasodifiy 20 tasi), imtihon (hali yopiq),
           4 ta amaliy topshiriq va "Python" guruhi. Qayta ishga tushirsa, mavjudini o'zgartirmaydi.
students — botda ro'yxatdan o'tganlar va ular guruhdami.
enroll   — guruhga hali qo'shilmagan hamma o'quvchini qo'shadi (EXCLUDE=5,9 — shu ID'larsiz).
open     — imtihonni hozir ochadi (HOURS=3 soatga) va o'quvchilarga botda xabar yuboradi.
status   — kim test ishladi, natija, nechta amaliy topshiriq yuborildi.
close    — muddatidan oldin yopish (hamma tugatgan bo'lsa); natija baholangach boradi.
remove   — PHONES=+998...,+998... — guruh va imtihondan chiqarish (akkaunt qoladi); `enroll`
           ularni qayta qo'shmaydi.

Savollar banki alohida modulda: offlayn guruhda "dars o'tildi" deb belgilanmagan darsning testi
o'quvchiga yopiq, shuning uchun savollarni oldindan ko'rib bo'lmaydi; imtihon esa ularni oladi.
"""

import os
from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Category, Course, Lesson, Module
from apps.exams import services as exam_services
from apps.exams.models import Exam, ExamAttempt, ExamTask, TaskAnswer
from apps.learning.models import Enrollment, StudyGroup
from apps.quizzes.models import Quiz
from apps.quizzes.parser import parse
from apps.quizzes.services import import_questions
from apps.users.models import SocialAccount, User
from apps.users.roles import Role, role_names, set_roles

ACTION = os.environ.get("ACTION", "setup")
COURSE_SLUG = "python"
GROUP_NAME = "Python"
MONTH = date(2026, 10, 1)
BANK_MODULE = "Oktabr imtihoni — savollar banki"

QUESTIONS = r"""
# 1-mavzu: Python haqida, o'rnatish, sintaktik xatolar, arifmetik amallar, print()

? Python qanday dasturlash tili?
+ Yuqori darajali, interpretatsiya qilinadigan, umumiy maqsadli til
- Faqat mashina kodida yoziladigan quyi darajali til
- Faqat veb-sahifalarni bezash uchun belgilash tili
- Faqat Windows'da ishlaydigan til
> Python — yuqori darajali, interpretatsiya qilinadigan (kod qatorma-qator bajariladigan) til.

? Python o'rnatishda terminalda python buyrug'i ishlashi uchun qaysi belgi qo'yiladi?
+ Add python.exe to PATH
- Disable path length limit
- Install for all users
- Customize installation
> PATH'ga qo'shilsa, Windows python buyrug'ini istalgan papkadan topadi.

? Quyidagi kod nima chiqaradi?
```python
print(10 + 5 * 2)
```
= 20
> Avval ko'paytirish bajariladi: 5 * 2 = 10, keyin qo'shish: 10 + 10 = 20.

? 7 // 2 va 7 % 2 ning natijalari qanday?
+ 3 va 1
- 3.5 va 1
- 3 va 0.5
- 4 va 1
> // — butun qismli bo'lish (3), % — bo'linmaning qoldig'i (1).

? Quyidagi kod ishga tushirilganda qanday xato chiqadi?
```python
print("Salom"
```
+ SyntaxError — qavs yopilmagan
- NameError — o'zgaruvchi topilmadi
- TypeError — turlar mos emas
- ZeroDivisionError — nolga bo'lish
> Ochilgan qavs yopilmagan — bu sintaktik xato (SyntaxError), dastur umuman ishga tushmaydi.

? Python dasturini yozib ishga tushirish bosqichlarini tartib bilan joylashtiring.
1. Python'ni o'rnatish
2. Kodni .py faylga yozish
3. Faylni saqlash
4. Terminalda python fayl.py buyrug'ini berish

# 2-mavzu: o'zgaruvchilar va ma'lumot turlari

? Qaysi o'zgaruvchi nomi Python'da to'g'ri?
+ ism_familiya
- 2ism
- ism-familiya
- class
> Nom raqam bilan boshlanmaydi, unda "-" bo'lmaydi, class kabi kalit so'zlar nom bo'la olmaydi.

? type(3.14) nima qaytaradi?
+ <class 'float'>
- <class 'int'>
- <class 'str'>
- <class 'decimal'>
> Kasr qismli son — float (haqiqiy son) turi.

? Qiymatni uning turi bilan moslang.
10 :: int
"10" :: str
10.5 :: float
True :: bool
> Qo'shtirnoq ichidagi har qanday qiymat — matn (str).

? Qaysilari ketma-ketlik (sequence) turlariga kiradi? Bir nechta javob bor.
+ list
+ tuple
+ range
- dict
- set
> Ketma-ketlik turlari: list, tuple, range. dict — kalit:qiymat (mapping) turi, set — to'plam turi.

? Quyidagi kod nima chiqaradi?
```python
s = {1, 2, 2, 3, 3}
print(len(s))
```
= 3
> To'plam (set) bir xil elementlarni takrorlab saqlamaydi: {1, 2, 3}.

? bool(0) va bool("0") natijalari qanday?
+ False va True
- False va False
- True va True
- True va False
> 0 soni — False. Bo'sh bo'lmagan har qanday matn, hatto "0" ham — True.

# 3-mavzu: string metodlari

? Quyidagi kod nima chiqaradi?
```python
s = "python"
print(s.upper())
```
+ PYTHON
- Python
- python
- pYTHON
> upper() barcha harflarni katta qiladi.

? strip() metodi nima qiladi?
+ Matnning boshidagi va oxiridagi bo'sh joylarni olib tashlaydi
- Matndagi barcha bo'sh joylarni, o'rtadagilarini ham olib tashlaydi
- Matnni teskari tartibda qaytaradi
- Matnni so'zlarga bo'lib ro'yxat qaytaradi

? Quyidagi kod nima chiqaradi?
```python
s = "olma,anor,uzum"
print(s.split(","))
```
+ ['olma', 'anor', 'uzum']
- ('olma', 'anor', 'uzum')
- olma anor uzum
- ['olma,anor,uzum']
> split(",") matnni vergul bo'yicha bo'lib, ro'yxat (list) qaytaradi.

? Quyidagi kod nima chiqaradi?
```python
s = "banan"
print(s.count("a"))
```
= 2
> "banan" so'zida "a" harfi 2 marta uchraydi.

? Quyidagi kod nima chiqaradi?
```python
s = "Salom dunyo"
print(s.replace("dunyo", "Python"))
```
+ Salom Python
- Salom dunyo
- Python dunyo
- SalomPython

? Quyidagi kod nima chiqaradi?
```python
s = "Python"
print(s[0], s[-1])
```
+ P n
- P o
- y n
- IndexError xatosi
> Indeks 0 dan boshlanadi: s[0] — birinchi belgi, s[-1] — oxirgi belgi.

# 4-mavzu: math metodlari

? Quyidagi kod nima chiqaradi?
```python
print(round(3.14159, 2))
```
= 3.14
= 3,14
> round(x, 2) — verguldan keyin 2 xonagacha yaxlitlaydi.

? Quyidagi kod nima chiqaradi?
```python
print(max(3, 7, 1), min(3, 7, 1), abs(-5))
```
+ 7 1 5
- 3 1 5
- 7 1 -5
- 7 3 5
> max — eng kattasi (7), min — eng kichigi (1), abs — musbat qiymati (5).

? Quyidagi kod nima chiqaradi?
```python
import math
print(math.ceil(4.1), math.floor(4.9))
```
+ 5 4
- 4 5
- 4 4
- 5 5
> ceil — yuqoriga (5), floor — pastga (4) eng yaqin butun songa yaxlitlaydi.

? Quyidagi kod nima chiqaradi?
```python
import math
print(math.gcd(12, 18))
```
= 6
> 12 va 18 ning eng katta umumiy bo'luvchisi (EKUB) — 6.

? Quyidagi kod nima chiqaradi?
```python
import math
print(math.sqrt(16))
```
+ 4.0
- 4
- 8.0
- 256
> math.sqrt doim haqiqiy son (float) qaytaradi: 4.0.

? Quyidagi kod nima chiqaradi?
```python
import math
print(math.log10(1000), pow(2, 5))
```
+ 3.0 32
- 3 32
- 100.0 10
- 3.0 10
> log10(1000) = 3.0, chunki 10 ning 3-darajasi 1000; pow(2, 5) = 32.

# 5-mavzu: shartli, mantiqiy va taqqoslash operatorlari

? Quyidagi kod nima chiqaradi?
```python
x = 7
if x > 10:
    print("katta")
elif x > 5:
    print("o'rtacha")
else:
    print("kichik")
```
+ o'rtacha
- katta
- kichik
- Hech narsa chiqmaydi
> x > 10 yolg'on, x > 5 rost — shuning uchun elif bloki ishlaydi.

? print(5 == 5.0) nima chiqaradi?
+ True
- False
- TypeError xatosi
- 5.0
> == qiymatlarni solishtiradi: 5 va 5.0 teng.

? Quyidagi kod nima chiqaradi?
```python
print(not True or False)
```
+ False
- True
- None
- SyntaxError xatosi
> Avval not bajariladi: not True = False; keyin False or False = False.

? Python'da "teng emas" taqqoslash operatori qaysi?
+ !=
- <>
- =!
- ==

? Mantiqiy operatorni uning ma'nosi bilan moslang.
and :: ikkala shart ham rost bo'lsa — rost
or :: kamida bitta shart rost bo'lsa — rost
not :: qiymatni teskarisiga aylantiradi

# 6-mavzu: ro'yxat (list) bilan tanishuv

? Quyidagi kod nima chiqaradi?
```python
mevalar = ["olma", "anor", "uzum"]
print(mevalar[1])
```
+ anor
- olma
- uzum
- IndexError xatosi
> Ro'yxat indeksi 0 dan boshlanadi: [0] — olma, [1] — anor.

? Ro'yxat (list) oxiriga yangi element qo'shadigan metod qaysi?
+ append()
- add()
- push()
- insert_end()
> list.append(x) — x ni ro'yxat oxiriga qo'shadi.

? Quyidagi kod nima chiqaradi?
```python
sonlar = [4, 8, 15, 16]
print(len(sonlar))
```
= 4
> len() ro'yxatdagi elementlar sonini qaytaradi.
"""

TASKS = [
    (
        "1. Arifmetik amallar",
        """O'zgaruvchilar berilgan: a = 17, b = 5.
print() yordamida har birini alohida qatorda, izohi bilan chiqaring:
1) yig'indi, 2) ayirma, 3) ko'paytma, 4) bo'linma (/), 5) butun bo'linma (//), 6) qoldiq (%),
7) a ning b-darajasi (**).

Kutilgan natija:
Yig'indi: 22
Ayirma: 12
Ko'paytma: 85
Bo'linma: 3.4
Butun bo'linma: 3
Qoldiq: 2
Daraja: 1419857

Kodni "Kod" maydoniga qo'ying.""",
    ),
    (
        "2. Matn bilan ishlash (string metodlari)",
        """O'zgaruvchi berilgan: matn = "  python dasturlash tili  "
Quyidagilarni bajaring va har bir natijani chiqaring:
1) chetidagi bo'sh joylarni olib tashlang (strip);
2) hosil bo'lgan matnni katta harflarda chiqaring (upper);
3) matnda "a" harfi necha marta uchrashini chiqaring (count);
4) "tili" so'zini "kursi" so'ziga almashtiring (replace);
5) matnni so'zlarga ajrating (split) va so'zlar sonini chiqaring (len).

Kutilgan natija:
python dasturlash tili
PYTHON DASTURLASH TILI
2
python dasturlash kursi
3""",
    ),
    (
        "3. Math metodlari",
        """math modulini ulang (import math) va hisoblab chiqaring:
1) 144 ning kvadrat ildizi (sqrt);
2) 7.3 ni yuqoriga va pastga yaxlitlash (ceil, floor);
3) 48 va 36 ning EKUBi (gcd);
4) 64 ning 2-asosli logarifmi (log2);
5) 2.71828 ni verguldan keyin 2 xonagacha yaxlitlash (round);
6) -15 ning musbat qiymati (abs) va 3 ning 4-darajasi (pow).

Kutilgan natija:
12.0
8 7
12
6.0
2.72
15 81""",
    ),
    (
        "4. Shartli operatorlar: baho",
        """ball o'zgaruvchisi berilgan (masalan, ball = 78). Baho chiqaradigan dastur yozing:
86–100 → "A'lo (5)"
71–85 → "Yaxshi (4)"
56–70 → "Qoniqarli (3)"
0–55 → "Qoniqarsiz (2)"
0 dan kichik yoki 100 dan katta → "Noto'g'ri ball"
if / elif / else va mantiqiy operatorlardan (and, or) foydalaning. Ball to'g'ri bo'lsa, uning
juft yoki toqligini ham chiqaring (% operatori bilan).

Tekshirish:
ball = 78 → Yaxshi (4), Juft
ball = 55 → Qoniqarsiz (2), Toq
ball = 101 → Noto'g'ri ball""",
    ),
]


def teacher() -> User:
    phone = os.environ.get("TEACHER_PHONE", "")
    users = User.objects.filter(is_active=True, is_superuser=True).order_by("date_joined")
    found = users.filter(phone=phone).first() if phone else users.first()
    if found is None:
        raise SystemExit("Admin topilmadi: avval `createsuperuser` qiling.")
    return found


def course() -> Course:
    found = Course.objects.filter(slug=COURSE_SLUG).first()
    if found is None:
        raise SystemExit("Kurs topilmadi: avval ACTION=setup.")
    return found


def exam() -> Exam:
    return Exam.objects.get(course=course(), month=MONTH)


def group() -> StudyGroup:
    return StudyGroup.objects.get(course=course(), name=GROUP_NAME)


def name_of(user: User) -> str:
    return f"{user.first_name} {user.last_name}".strip() or "(ismsiz)"


@transaction.atomic
def setup() -> None:
    owner = teacher()
    roles = role_names(owner)
    if Role.TEACHER not in roles:
        set_roles(owner, {*roles, Role.TEACHER})
    category, _ = Category.objects.get_or_create(slug="dasturlash", defaults={"name": "Dasturlash"})
    python, _ = Course.objects.get_or_create(
        slug=COURSE_SLUG,
        defaults={
            "title": "Python",
            "category": category,
            "study_format": Course.Format.OFFLINE,
            "monthly_exam": True,
            "certificate": False,
        },
    )
    module, _ = Module.objects.get_or_create(
        course=python, title=BANK_MODULE, defaults={"order": 1000}
    )
    lesson, _ = Lesson.objects.get_or_create(
        module=module, title="Oktabr oylik imtihoni", defaults={"order": 1}
    )
    quiz, _ = Quiz.objects.get_or_create(
        lesson=lesson, defaults={"title": "Oktabr imtihoni savollari"}
    )
    if not quiz.questions.exists():
        import_questions(quiz, parse(QUESTIONS))
    StudyGroup.objects.get_or_create(
        course=python,
        name=GROUP_NAME,
        defaults={"teacher": owner, "study_format": "OFFLINE", "starts_on": timezone.localdate()},
    )
    now = timezone.now()
    test, created = Exam.objects.get_or_create(
        course=python,
        month=MONTH,
        defaults={
            "status": Exam.Status.DRAFT,
            "questions_count": 20,
            "duration_min": 40,
            "pass_percent": 60,
            "test_weight": 50,
            "opens_at": now + timedelta(days=30),
            "closes_at": now + timedelta(days=31),
            "created_by": owner,
        },
    )
    if created:
        test.modules.set([module])
    if not test.tasks.exists():
        for order, (title, instructions) in enumerate(TASKS, start=1):
            ExamTask.objects.create(exam=test, order=order, title=title, instructions=instructions)
    print(
        f"Kurs: {python.title} (id {python.pk}), guruh: {GROUP_NAME}, o'qituvchi: {name_of(owner)}"
    )
    print(
        f"Savollar banki: {quiz.questions.count()} ta, imtihonda: {test.questions_count} ta, "
        f"{test.duration_min} daqiqa, o'tish {test.pass_percent}%"
    )
    print(
        f"Amaliy topshiriqlar: {test.tasks.count()} ta. Imtihon holati: {test.get_status_display()}"
    )


def students() -> list[User]:
    python = course()
    linked = set(
        SocialAccount.objects.filter(provider=SocialAccount.Provider.TELEGRAM).values_list(
            "user_id", flat=True
        )
    )
    enrolled = set(
        Enrollment.objects.filter(course=python, status=Enrollment.Status.ACTIVE).values_list(
            "user_id", flat=True
        )
    )
    people = list(User.objects.filter(is_active=True, is_staff=False).order_by("date_joined"))
    yes, no = "ha", "yo'q"
    print(f"{'ID':>4}  {'Ism':28} {'Telefon':14} Telegram  Guruhda")
    for user in people:
        telegram = yes if user.pk in linked else no
        member = yes if user.pk in enrolled else no
        print(f"{user.pk:>4}  {name_of(user)[:28]:28} {user.phone:14} {telegram:9} {member}")
    print(f"Jami: {len(people)}, guruhda: {len(enrolled)}")
    return people


@transaction.atomic
def enroll() -> None:
    python, team = course(), group()
    skip = {int(value) for value in os.environ.get("EXCLUDE", "").split(",") if value.strip()}
    added = []
    for user in User.objects.filter(is_active=True, is_staff=False).exclude(pk__in=skip):
        # Guruhdagilar ham, `remove` bilan chiqarilganlar ham (bekor qilingan yozilish) o'tkaziladi.
        if Enrollment.objects.filter(user=user, course=python).exists():
            continue
        Enrollment.objects.create(
            user=user,
            course=python,
            group=team,
            status=Enrollment.Status.ACTIVE,
            source=Enrollment.Source.MANUAL,
            study_format=Enrollment.Format.OFFLINE,
        )
        added.append(name_of(user))
    print(f"Guruhga qo'shildi: {len(added)}")
    for name in added:
        print(f"  + {name}")


def open_exam() -> None:
    test = exam()
    hours = float(os.environ.get("HOURS", "3"))
    now = timezone.now()
    Exam.objects.filter(pk=test.pk).update(
        status=Exam.Status.READY,
        opens_at=now,
        closes_at=now + timedelta(hours=hours),
        opened_notified_at=None,
    )
    sent = exam_services.announce_open(now=now)
    closes = timezone.localtime(now + timedelta(hours=hours))
    print(f"Imtihon ochildi, {closes:%H:%M} da yopiladi. Xabar yuborildi: {sent} ta o'quvchiga.")


def status() -> None:
    test = exam()
    people = list(exam_services.participants(test))
    attempts = {item.student_id: item for item in ExamAttempt.objects.filter(exam=test)}
    tasks = test.tasks.count()
    print(
        f"Imtihon: {test.get_status_display()}, "
        f"{timezone.localtime(test.opens_at):%d.%m %H:%M} – "
        f"{timezone.localtime(test.closes_at):%H:%M}"
    )
    print(f"{'Ism':28} {'Test':12} Amaliy")
    for user in people:
        attempt = attempts.get(user.pk)
        if attempt is None:
            test_state = "boshlamagan"
        elif attempt.finished_at is None:
            test_state = "ishlayapti"
        else:
            test_state = f"{attempt.score}%"
        sent = TaskAnswer.objects.filter(task__exam=test, student=user).count()
        print(f"{name_of(user)[:28]:28} {test_state:12} {sent}/{tasks}")
    print(f"Qatnashchilar: {len(people)}")


@transaction.atomic
def remove() -> None:
    """Guruh va imtihondan chiqarish (akkaunt qoladi): PHONES=+998901234567,+998..."""
    python, team = course(), group()
    phones = [value.strip() for value in os.environ.get("PHONES", "").split(",") if value.strip()]
    if not phones:
        raise SystemExit("Telefonlar kerak: -e PHONES=+998901234567,+998...")
    for phone in phones:
        user = User.objects.filter(phone=phone).first()
        if user is None:
            print(f"  ? {phone} — topilmadi")
            continue
        Enrollment.objects.update_or_create(
            user=user,
            course=python,
            defaults={
                "status": Enrollment.Status.CANCELLED,
                "group": team,
                "study_format": Enrollment.Format.OFFLINE,
            },
        )
        print(f"  - {name_of(user)} ({phone}) — guruh va imtihondan chiqarildi")


def close_exam() -> None:
    """Muddatidan oldin yopish: javob qabul qilinmaydi, tugatilmagan testlar yakunlanadi.
    Yakuniy natija o'quvchiga uning amaliy topshiriqlari baholangach boradi."""
    test = exam()
    now = timezone.now()
    if test.closes_at > now:
        Exam.objects.filter(pk=test.pk).update(closes_at=now)
    finished = 0
    for attempt in ExamAttempt.objects.filter(exam=test, finished_at__isnull=True):
        exam_services.finish_test(attempt, now=now)
        finished += 1
    print(f"Imtihon yopildi ({timezone.localtime(now):%H:%M}). Yakunlangan testlar: {finished}.")
    print("Natija har bir o'quvchiga amaliy topshiriqlari baholangach yuboriladi.")
    status()


ACTIONS = {
    "setup": setup,
    "students": students,
    "enroll": enroll,
    "open": open_exam,
    "close": close_exam,
    "remove": remove,
    "status": status,
}
if ACTION not in ACTIONS:
    raise SystemExit(f"ACTION: {', '.join(ACTIONS)}")
ACTIONS[ACTION]()
