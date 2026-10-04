"""Python guruhi: o'tilgan 6 ta mavzuga dars testlari — kunlik test savollar banki.

Serverda, /srv/sifatedu papkasida (kod Django shell'ga uzatiladi, image qayta yig'ilmaydi):

  S=backend/scripts/python_dars_testlari.py
  dc exec -T -e ACTION=setup  backend python manage.py shell < $S
  dc exec -T -e ACTION=status backend python manage.py shell < $S

setup  — «Python asoslari» moduli: 6 ta dars (mavzu), har birida 14 ta savol (jami 84 ta,
         oktabr imtihonidagilardan boshqa). Darslar «Python» guruhi uchun o'tilgan deb
         belgilanadi (o'quvchilarga xabar yuborilmaydi), guruh holati «O'qiyapti» bo'ladi —
         ertangi 07:00 dan kunlik test shu savollardan beriladi. Qayta ishga tushirsa,
         mavjudini o'zgartirmaydi. EXAM=1 — oktabr imtihoni savollarini ham bankka qo'shadi
         (imtihon tugagan; ular o'quvchilarga dars testi sifatida ham ochiladi).
status — guruh holati, o'tilgan darslar, kunlik test uchun savollar soni va bugungi test.

Keyingi mavzular: admin → Darslar → yangi dars + test («Tez kiritish»), so'ng jonli darsda
«Dars o'tildi» yoki guruh sahifasidagi «O'tilgan darslar».
"""

import os

from django.db import transaction

from apps.catalog.models import Course, Lesson, Module
from apps.dailytest import services as daily
from apps.dailytest.models import DailyTest
from apps.learning.models import StudyGroup
from apps.live.models import GroupLesson
from apps.quizzes.models import Quiz
from apps.quizzes.parser import parse
from apps.quizzes.services import import_questions
from apps.rewards import services as rewards

ACTION = os.environ.get("ACTION", "setup")
COURSE_SLUG = os.environ.get("COURSE", "python")
GROUP_NAME = os.environ.get("GROUP", "Python")
MODULE = "Python asoslari"
EXAM_MODULE = "Oktabr imtihoni — savollar banki"

TOPICS = [
    (
        "1-mavzu: Python haqida, sintaktik xatolar, arifmetik amallar, print()",
        r"""
? Python dasturi fayli qaysi kengaytma bilan saqlanadi?
+ .py
- .pt
- .python
- .txt

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
print(2 + 3 * 4)
```
= 14
> Avval ko'paytirish: 3 * 4 = 12, keyin qo'shish: 2 + 12 = 14.

? Quyidagi kod nima chiqaradi?
```python
print((2 + 3) * 4)
```
+ 20
- 14
- 24
- 9
> Qavs ichidagi amal birinchi bajariladi: (2 + 3) = 5, 5 * 4 = 20.

? Quyidagi kod nima chiqaradi?
```python
print(15 / 4)
```
+ 3.75
- 3
- 3.7
- 4
> / — oddiy bo'lish, natija doim haqiqiy son (float).

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
print(15 // 4)
```
= 3
> // — butun bo'lish: kasr qismi tashlab yuboriladi.

? Quyidagi kod nima chiqaradi?
```python
print(15 % 4)
```
+ 3
- 3.75
- 1
- 4
> % — qoldiq: 15 = 4 * 3 + 3.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
print(2 ** 4)
```
= 16
> ** — darajaga ko'tarish: 2 * 2 * 2 * 2 = 16.

? Quyidagi kod nima chiqaradi?
```python
print("Salom", "dunyo")
```
+ Salom dunyo
- Salomdunyo
- Salom,dunyo
- "Salom" "dunyo"
> print() qiymatlar orasiga standart holatda bitta bo'sh joy qo'yadi.

? Quyidagi kod nima chiqaradi?
```python
print("A", "B", sep="-")
```
+ A-B
- A B
- AB
- A - B
> sep — qiymatlar orasiga qo'yiladigan belgi.

? Quyidagi kod nima chiqaradi?
```python
print("Python" * 3)
```
+ PythonPythonPython
- Python 3
- Python*3
- Xato beradi
> Matnni songa ko'paytirsa, matn shuncha marta takrorlanadi.

? Qaysi qator SyntaxError beradi?
+ print("Salom')
- print("Salom")
- print('Salom')
- print("Salom", 5)
> Qo'shtirnoq bir xil bo'lishi kerak: " bilan ochilgan matn " bilan yopiladi.

? Python'da izoh (kommentariya) qaysi belgi bilan yoziladi?
+ #
- //
- /* */
- --
> # dan keyingi matnni Python bajarmaydi.

? Quyidagi kod nima chiqaradi?
```python
print(10 / 2)
```
+ 5.0
- 5
- 5.00
- 2
> / har doim float qaytaradi, natija butun bo'lsa ham.

? Qaysilari arifmetik operator? Hammasini belgilang.
+ **
+ %
+ //
- ==
- and
> == — taqqoslash, and — mantiqiy operator.
""",
    ),
    (
        "2-mavzu: o'zgaruvchilar va ma'lumot turlari",
        r"""
? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
x = 5
x = x + 2
print(x)
```
= 7
> x ning yangi qiymati: 5 + 2 = 7.

? type("5") nima qaytaradi?
+ <class 'str'>
- <class 'int'>
- <class 'float'>
- <class 'char'>
> Qo'shtirnoq ichidagi qiymat — matn (str).

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
print(int("12") + 3)
```
= 15
> int("12") matnni songa aylantiradi: 12 + 3 = 15.

? Quyidagi kod nima chiqaradi?
```python
print("12" + "3")
```
+ 123
- 15
- 12 3
- Xato beradi
> Ikki matn qo'shilsa, ular yopishtiriladi.

? Quyidagi kod nima chiqaradi?
```python
print(int(7.9))
```
+ 7
- 8
- 7.9
- Xato beradi
> int() kasr qismini tashlab yuboradi (yaxlitlamaydi).

? Quyidagi kod nima chiqaradi?
```python
print(float(3))
```
+ 3.0
- 3
- 3.00
- "3.0"
> float() butun sonni haqiqiy songa aylantiradi.

? Quyidagi kod nima chiqaradi?
```python
print(str(10) * 2)
```
+ 1010
- 20
- 10 10
- Xato beradi
> str(10) — matn "10", matn 2 marta takrorlanadi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
a, b = 2, 5
print(a * b)
```
= 10
> Bir qatorda ikki o'zgaruvchi: a = 2, b = 5.

? Qaysi qiymat bool turida?
+ True
- "True"
- 1
- "False"
> Qo'shtirnoqdagi "True" — matn, 1 — butun son.

? Quyidagi kod nima chiqaradi?
```python
print(type(10 > 3))
```
+ <class 'bool'>
- <class 'int'>
- <class 'str'>
- True
> Taqqoslash natijasi — True yoki False, ya'ni bool.

? ism va Ism — bitta o'zgaruvchimi?
+ Yo'q, Python katta-kichik harfni farqlaydi — bular ikki xil o'zgaruvchi
- Ha, bitta o'zgaruvchi
- Faqat funksiyalarda farq qiladi
- Xato beradi
> Python katta va kichik harflarni farqlaydi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
x = 4
x *= 3
print(x)
```
= 12
> x *= 3 — bu x = x * 3 degani.

? Funksiyani natijasi bilan moslang:
int("8") :: 8
float("2.5") :: 2.5
str(3) :: "3"
bool("") :: False
> Bo'sh matn bool'da False, bo'sh bo'lmagani — True.

? None qiymati nimani bildiradi?
+ Qiymat yo'qligini
- Nol sonini
- Bo'sh matnni
- Xatoni
""",
    ),
    (
        "3-mavzu: string metodlari",
        r"""
? Quyidagi kod nima chiqaradi?
```python
print("Python".lower())
```
+ python
- PYTHON
- Python
- pYTHON
> lower() barcha harflarni kichik qiladi.

? Quyidagi kod nima chiqaradi?
```python
print("salom dunyo".title())
```
+ Salom Dunyo
- Salom dunyo
- SALOM DUNYO
- salom Dunyo
> title() har bir so'zning birinchi harfini katta qiladi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
print(len("Salom!"))
```
= 6
> len() barcha belgilarni sanaydi, "!" ham belgi.

? Quyidagi kod nima chiqaradi?
```python
print("dastur".capitalize())
```
+ Dastur
- DASTUR
- dastuR
- dastur
> capitalize() faqat birinchi harfni katta qiladi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
print("olma".find("m"))
```
= 2
> find() birinchi uchragan o'rinni qaytaradi: o — 0, l — 1, m — 2.

? Quyidagi kod nima chiqaradi?
```python
print("abc".find("z"))
```
+ -1
- 0
- None
- Xato beradi
> Topilmasa, find() -1 qaytaradi.

? Quyidagi kod nima chiqaradi?
```python
print("dasturlash"[0:6])
```
+ dastur
- dastu
- asturl
- dasturl
> Kesim [0:6] — 0 dan 5 gacha (6 kirmaydi).

? Quyidagi kod nima chiqaradi?
```python
print("ab" + "cd".upper())
```
+ abCD
- ABCD
- abcd
- ABcd
> upper() faqat "cd" ga qo'llanadi, keyin matnlar qo'shiladi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
print(len("  salom  ".strip()))
```
= 5
> strip() chetidagi bo'sh joylarni olib tashlaydi: "salom" — 5 ta harf.

? Quyidagi kod nima chiqaradi?
```python
print("-".join(["a", "b", "c"]))
```
+ a-b-c
- abc
- a b c
- ['a', 'b', 'c']
> join() ro'yxat elementlarini berilgan belgi bilan birlashtiradi.

? Quyidagi kod nima chiqaradi?
```python
print("salom".startswith("sa"))
```
+ True
- False
- sa
- Xato beradi

? Quyidagi kod nima chiqaradi?
```python
print("Ali" in "Alisher")
```
+ True
- False
- Ali
- Xato beradi
> in — matn ichida bormi yoki yo'qligini tekshiradi.

? Quyidagi kod nima chiqaradi?
```python
print("python"[::-1])
```
+ nohtyp
- python
- p
- Xato beradi
> [::-1] — matnni teskari tartibda qaytaradi.

? Metodni vazifasi bilan moslang:
upper() :: katta harfga o'giradi
lower() :: kichik harfga o'giradi
replace() :: matn qismini almashtiradi
split() :: matnni bo'lib, ro'yxat qaytaradi
""",
    ),
    (
        "4-mavzu: math metodlari",
        r"""
? Quyidagi kod nima chiqaradi?
```python
import math
print(math.pi)
```
+ 3.141592653589793
- 3.14
- 22/7
- 3
> math.pi — π sonining aniq qiymati (15–16 xonagacha).

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
print(abs(-12))
```
= 12
> abs() — sonning musbat qiymati (moduli).

? Quyidagi kod nima chiqaradi?
```python
print(round(7.6))
```
+ 8
- 7
- 7.6
- 8.0
> round() eng yaqin butun songa yaxlitlaydi va int qaytaradi.

? Quyidagi kod nima chiqaradi?
```python
print(round(2.5))
```
+ 2
- 3
- 2.5
- 3.0
> Python teng yarimni juft songa yaxlitlaydi: round(2.5) = 2, round(3.5) = 4.

? Quyidagi kod nima chiqaradi?
```python
import math
print(math.sqrt(81))
```
+ 9.0
- 9
- 81
- 40.5
> math.sqrt doim float qaytaradi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
print(pow(3, 2))
```
= 9
> pow(3, 2) — 3 ning 2-darajasi.

? Quyidagi kod nima chiqaradi?
```python
import math
print(math.floor(-2.5))
```
+ -3
- -2
- -2.5
- 2
> floor — pastga (kichik tomonga) yaxlitlaydi: -2.5 dan pastdagi butun son — -3.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
import math
print(math.ceil(2.1))
```
= 3
> ceil — yuqoriga yaxlitlaydi.

? Quyidagi kod nima chiqaradi?
```python
print(max([4, 9, 2]))
```
+ 9
- 4
- 2
- [4, 9, 2]

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
print(sum([1, 2, 3, 4]))
```
= 10
> sum() ro'yxat elementlarini qo'shadi.

? Quyidagi kod nima chiqaradi?
```python
import math
print(math.factorial(4))
```
+ 24
- 16
- 10
- 4
> 4! = 1 * 2 * 3 * 4 = 24.

? Quyidagi kod nima chiqaradi?
```python
print(min(5, -1, 3))
```
+ -1
- 3
- 5
- 1

? math modulidan foydalanish uchun nima yoziladi?
+ import math
- include math
- using math
- math.import()

? Ifodani natijasi bilan moslang:
math.sqrt(25) :: 5.0
math.ceil(1.2) :: 2
math.floor(1.8) :: 1
abs(-7) :: 7
""",
    ),
    (
        "5-mavzu: shartli, mantiqiy va taqqoslash operatorlari",
        r"""
? Quyidagi kod nima chiqaradi?
```python
print(10 > 3 and 2 > 5)
```
+ False
- True
- 10
- Xato beradi
> and — ikkala shart ham rost bo'lishi kerak; 2 > 5 yolg'on.

? Quyidagi kod nima chiqaradi?
```python
print(10 > 3 or 2 > 5)
```
+ True
- False
- 2
- Xato beradi
> or — kamida bittasi rost bo'lsa yetarli.

? Quyidagi kod nima chiqaradi?
```python
print(not 5 > 3)
```
+ False
- True
- 5
- Xato beradi
> Avval 5 > 3 = True, keyin not True = False.

? Quyidagi kod nima chiqaradi?
```python
yosh = 16
if yosh >= 18:
    print("katta")
else:
    print("kichik")
```
+ kichik
- katta
- katta kichik
- Hech narsa chiqmaydi

? Quyidagi kod nima chiqaradi?
```python
n = 0
if n:
    print("bor")
else:
    print("yo'q")
```
+ yo'q
- bor
- 0
- Xato beradi
> 0 soni shartda False hisoblanadi.

? Quyidagi kod nima chiqaradi?
```python
print(3 != 3)
```
+ False
- True
- 3
- Xato beradi

? Quyidagi kod nima chiqaradi?
```python
print(5 >= 5)
```
+ True
- False
- 5
- Xato beradi
> >= — katta yoki teng; 5 = 5.

? Quyidagi kod nima chiqaradi?
```python
ball = 85
if ball >= 90:
    print("A")
elif ball >= 80:
    print("B")
elif ball >= 70:
    print("C")
else:
    print("D")
```
+ B
- A
- C
- D
> Shartlar tepadan tekshiriladi; birinchi rost shart — ball >= 80.

? Quyidagi kod nima chiqaradi?
```python
print("a" < "b")
```
+ True
- False
- Xato beradi
- a
> Matnlar alifbo tartibida solishtiriladi.

? Quyidagi kod nima chiqaradi?
```python
print(2 < 5 < 10)
```
+ True
- False
- Xato beradi
- 5
> Python'da taqqoslashni zanjir qilib yozish mumkin: 2 < 5 va 5 < 10.

? x = 7 bo'lsa, qaysi shart rost?
+ x % 2 == 1
- x % 2 == 0
- x > 10
- x == "7"
> 7 toq son: 2 ga bo'linganda qoldiq 1. 7 va "7" — har xil turlar.

? Python'da "teng" taqqoslash operatori qaysi?
+ ==
- =
- ===
- eq
> = — qiymat berish, == — taqqoslash.

? Quyidagi kod nima chiqaradi?
```python
print(True and not False)
```
+ True
- False
- None
- Xato beradi

? Ifodani ma'nosi bilan moslang:
a == b :: a va b teng
a != b :: a va b teng emas
a >= b :: a b dan katta yoki teng
a <= b :: a b dan kichik yoki teng
""",
    ),
    (
        "6-mavzu: ro'yxat (list) bilan tanishuv",
        r"""
? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
sonlar = [10, 20, 30]
print(sonlar[0])
```
= 10
> Indeks 0 dan boshlanadi.

? Quyidagi kod nima chiqaradi?
```python
sonlar = [10, 20, 30]
print(sonlar[-1])
```
+ 30
- 10
- 20
- Xato beradi
> -1 — oxirgi element.

? Quyidagi kod nima chiqaradi?
```python
a = [1, 2, 3]
a.append(4)
print(a)
```
+ [1, 2, 3, 4]
- [4, 1, 2, 3]
- [1, 2, 3]
- 4

? Quyidagi kod nima chiqaradi?
```python
a = [5, 3, 8]
a.sort()
print(a)
```
+ [3, 5, 8]
- [8, 5, 3]
- [5, 3, 8]
- None
> sort() ro'yxatni o'sish tartibida saralaydi.

? Quyidagi kod nima chiqaradi?
```python
a = [1, 2, 3]
a.insert(0, 9)
print(a)
```
+ [9, 1, 2, 3]
- [1, 2, 3, 9]
- [1, 9, 2, 3]
- [9]
> insert(0, 9) — 0-o'ringa 9 ni qo'yadi.

? Quyidagi kod nima chiqaradi?
```python
a = ["olma", "anor"]
a.remove("olma")
print(a)
```
+ ['anor']
- ['olma']
- []
- ['olma', 'anor']

? Quyidagi kod nima chiqaradi?
```python
a = [1, 2, 3, 4, 5]
print(a[1:3])
```
+ [2, 3]
- [1, 2, 3]
- [2, 3, 4]
- [1, 2]
> Kesim [1:3] — 1 va 2-indekslar (3 kirmaydi).

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
a = [3, 1, 2]
print(len(a) + a[0])
```
= 6
> len(a) = 3, a[0] = 3, jami 6.

? Quyidagi kod nima chiqaradi?
```python
a = [1, 2]
b = [3]
print(a + b)
```
+ [1, 2, 3]
- [4, 2]
- [[1, 2], [3]]
- Xato beradi
> Ikki ro'yxat qo'shilsa, ular birlashadi.

? Quyidagi kod nima chiqaradi?
```python
a = [7, 8, 9]
a.pop()
print(a)
```
+ [7, 8]
- [8, 9]
- [7, 8, 9]
- [9]
> pop() oxirgi elementni olib tashlaydi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
a = [4, 4, 5]
print(a.count(4))
```
= 2

? Quyidagi kod nima chiqaradi?
```python
a = ["x", "y", "z"]
print(a.index("z"))
```
+ 2
- 3
- z
- 1

? Qaysi ifoda bo'sh ro'yxat yaratadi?
+ []
- {}
- ()
- ""
> {} — bo'sh lug'at (dict), () — bo'sh kortej (tuple), "" — bo'sh matn.

? Quyidagi kod nima chiqaradi?
```python
a = [1, 2, 3]
a[1] = 20
print(a)
```
+ [1, 20, 3]
- [20, 2, 3]
- [1, 2, 20]
- Xato beradi
> Ro'yxat elementini o'zgartirish mumkin.
""",
    ),
]


def course() -> Course:
    found = Course.objects.filter(slug=COURSE_SLUG).first()
    if found is None:
        raise SystemExit(f"«{COURSE_SLUG}» kursi topilmadi.")
    return found


def group(python: Course) -> StudyGroup:
    found = StudyGroup.objects.filter(course=python, name=GROUP_NAME).first()
    if found is None:
        raise SystemExit(f"«{GROUP_NAME}» guruhi topilmadi.")
    return found


@transaction.atomic
def setup() -> None:
    python = course()
    team = group(python)
    module, _ = Module.objects.get_or_create(course=python, title=MODULE, defaults={"order": 1})
    lessons = []
    for number, (title, source) in enumerate(TOPICS, start=1):
        lesson, _ = Lesson.objects.get_or_create(
            module=module, title=title, defaults={"order": number}
        )
        quiz, _ = Quiz.objects.get_or_create(lesson=lesson, defaults={"title": f"{title} — test"})
        if not quiz.questions.exists():
            import_questions(quiz, parse(source))
        lessons.append(lesson)
        print(f"  {title}: {quiz.questions.count()} ta savol")
    if os.environ.get("EXAM") == "1":
        exam = Lesson.objects.filter(module__course=python, module__title=EXAM_MODULE).first()
        if exam is not None:
            lessons.append(exam)
            print(f"  + {exam.title} (imtihon savollari)")
    opened = 0
    for lesson in lessons:
        _record, created = GroupLesson.objects.get_or_create(
            group=team, lesson=lesson, defaults={"opened_by": team.teacher}
        )
        opened += created
    if team.status != StudyGroup.Status.ACTIVE:
        team.status = StudyGroup.Status.ACTIVE
        team.save(update_fields=["status", "updated_at"])
        print(f"Guruh holati: {team.get_status_display()}")
    need = rewards.settings().daily_test_questions
    have = len(daily.pool(team))
    print(f"O'tilgan deb belgilandi: {opened} ta dars (xabar yuborilmadi)")
    print(
        f"Kunlik test banki: {have} ta savol (kerak — kamida {need}). "
        + ("Ertaga 07:00 dan test beriladi." if have >= need else "Hali yetarli emas.")
    )


def status() -> None:
    python = course()
    team = group(python)
    covered = GroupLesson.objects.filter(group=team).select_related("lesson").order_by("opened_at")
    print(f"Guruh: {team.name} — {team.get_status_display()}, o'qituvchi: {team.teacher}")
    print(f"O'tilgan darslar: {covered.count()} ta")
    for record in covered:
        print(f"  - {record.lesson.title}")
    need = rewards.settings().daily_test_questions
    print(f"Kunlik test banki: {len(daily.pool(team))} ta savol (kerak — kamida {need})")
    today = DailyTest.objects.filter(group=team, day=daily.local_day()).first()
    if today is None:
        print("Bugun kunlik test yo'q.")
        return
    done = today.attempts.filter(finished_at__isnull=False).count()
    print(f"Bugungi test: {today.get_status_display()}, ishladi: {done} kishi")


if ACTION == "setup":
    setup()
elif ACTION == "status":
    status()
else:
    raise SystemExit(f"Noma'lum ACTION={ACTION}: setup yoki status.")
