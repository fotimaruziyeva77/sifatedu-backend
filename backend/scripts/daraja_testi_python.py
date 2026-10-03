"""Botdagi «🎯 Daraja testi» — Python yo'nalishi: savollar banki va test sozlamasi.

Serverda, /srv/sifatedu papkasida (kod Django shell'ga uzatiladi, image qayta yig'ilmaydi):

  S=backend/scripts/daraja_testi_python.py
  dc exec -T -e ACTION=setup  backend python manage.py shell < $S
  dc exec -T -e ACTION=status backend python manage.py shell < $S
  dc exec -T -e ACTION=off    backend python manage.py shell < $S
  dc exec -T -e ACTION=on     backend python manage.py shell < $S

setup  — «Daraja testlari» xizmat kursi (nashr qilinmaydi, hech kim yozilmaydi — savollarni
         oldindan ko'rib bo'lmaydi), unda 28 ta savol va «Python» daraja testi: har odamga
         tasodifiy 12 tasi, 15 daqiqa. Qayta ishga tushirsa, mavjudini o'zgartirmaydi.
status — nechta odam ishladi, o'rtacha natija, kuponlar va manbalar; oxirgi 15 ta natija.
off/on — testni vaqtincha o'chirish / yoqish (botdagi tugma ham yo'qoladi / chiqadi).

Savollarni keyin admin'da o'zgartirish mumkin: Kurslar → «Daraja testlari (xizmat kursi)» →
dars testi; test sozlamalari — Sotuv → Daraja testlari.
"""

import os

from django.db import transaction
from django.db.models import Avg, Count

from apps.catalog.models import Course, Lesson, Module
from apps.placement.models import PlacementAttempt, PlacementTest
from apps.quizzes.models import Quiz
from apps.quizzes.parser import parse
from apps.quizzes.services import import_questions

ACTION = os.environ.get("ACTION", "setup")
COURSE_SLUG = "python"
SERVICE_SLUG = "daraja-testlari"
TITLE = "Python"

QUESTIONS = r"""
? Python'da ekranga matn chiqaradigan funksiya qaysi?
+ print()
- input()
- echo()
- write()
> print() — ekranga chiqaradi, input() esa foydalanuvchidan ma'lumot oladi.

? Python'da izoh (kommentariya) qaysi belgi bilan boshlanadi?
+ #
- //
- <!--
- --
> # dan keyingi matnni Python bajarmaydi — bu dasturchi uchun eslatma.

? Python'da kod bloklari (if yoki for ichidagi qatorlar) qanday ajratiladi?
+ Qator boshidagi bo'shliq (chekinish) bilan
- Figurali qavslar { } bilan
- begin va end so'zlari bilan
- Nuqtali vergul ; bilan
> Python blokni chekinish bilan ajratadi; chekinish noto'g'ri bo'lsa — IndentationError.

? Qaysi o'zgaruvchi nomi Python'da XATO?
+ 2son
- son2
- _son
- son_2
> O'zgaruvchi nomi raqam bilan boshlanmaydi.

? Quyidagi kod nima chiqaradi?
```python
x = 5
y = 2
print(x * y)
```
+ 10
- 7
- 52
- xy
> * — ko'paytirish: 5 * 2 = 10.

? Quyidagi kod nima chiqaradi?
```python
print(7 // 2)
```
+ 3
- 3.5
- 4
- 1
> // — butun bo'lish: kasr qismi tashlab yuboriladi, 7 // 2 = 3.

? Quyidagi kod nima chiqaradi?
```python
print(10 % 3)
```
+ 1
- 3
- 3.33
- 0
> % — bo'linmaning qoldig'i: 10 = 3 * 3 + 1.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
print(2 ** 3)
```
= 8
> ** — darajaga ko'tarish: 2 * 2 * 2 = 8.

? Quyidagi kod nima chiqaradi?
```python
a = "5"
b = "3"
print(a + b)
```
+ 53
- 8
- 5 3
- Xato beradi
> Qo'shtirnoq ichidagi qiymat — matn (str); matnlar + bilan yopishtiriladi: "53".

? type(3.14) nimani qaytaradi?
+ <class 'float'>
- <class 'int'>
- <class 'str'>
- <class 'decimal'>
> Kasr sonlar Python'da float turida bo'ladi.

? input() foydalanuvchi kiritgan qiymatni qaysi turda qaytaradi?
+ str (matn)
- int (butun son)
- Kiritilganiga qarab int yoki float
- bool
> input() har doim matn qaytaradi; son kerak bo'lsa, int(input()) kabi o'giriladi.

? Quyidagilardan qaysilari Python'dagi ma'lumot turlari? Hammasini belgilang.
+ int
+ str
+ list
- char
> Python'da alohida char turi yo'q — bitta belgi ham str bo'ladi.

? Quyidagi kod nima chiqaradi?
```python
name = "Python"
print(len(name))
```
+ 6
- 5
- 7
- Python
> len() — uzunlik: P, y, t, h, o, n — 6 ta belgi.

? Quyidagi kod nima chiqaradi?
```python
s = "Salom"
print(s[0])
```
+ S
- a
- m
- Salom
> Indekslar 0 dan boshlanadi: s[0] — birinchi belgi.

? Quyidagi kod nima chiqaradi?
```python
s = "dastur"
print(s[-1])
```
+ r
- d
- u
- Xato beradi
> Manfiy indeks oxiridan sanaydi: s[-1] — oxirgi belgi.

? Quyidagi kod nima chiqaradi?
```python
s = "Python"
print(s[1:4])
```
+ yth
- Pyt
- ytho
- Pyth
> Kesim [1:4] — 1, 2 va 3-indekslar (4 kirmaydi): y, t, h.

? Quyidagi kod nima chiqaradi?
```python
ism = "Aziz"
print(f"Salom, {ism}!")
```
+ Salom, Aziz!
- Salom, {ism}!
- f"Salom, Aziz!"
- Xato beradi
> f-satrda {} ichiga o'zgaruvchining qiymati qo'yiladi.

? Quyidagi kod nima chiqaradi?
```python
x = 15
if x > 10:
    print("katta")
else:
    print("kichik")
```
+ katta
- kichik
- katta kichik
- Hech narsa chiqmaydi
> 15 > 10 — rost, shuning uchun if bloki bajariladi.

? Quyidagi kod nima chiqaradi?
```python
print(5 > 3 and 2 > 4)
```
+ False
- True
- 5
- Xato beradi
> and — ikkala shart ham rost bo'lsa True; 2 > 4 yolg'on, demak False.

? Quyidagi kod nima chiqaradi?
```python
for i in range(3):
    print(i)
```
+ 0, 1, 2 (har biri alohida qatorda)
- 1, 2, 3 (har biri alohida qatorda)
- 0, 1, 2, 3 (har biri alohida qatorda)
- 3
> range(3) — 0 dan boshlab 3 gacha (3 kirmaydi): 0, 1, 2.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
total = 0
for n in range(1, 5):
    total += n
print(total)
```
= 10
> 1 + 2 + 3 + 4 = 10 (range(1, 5) da 5 kirmaydi).

? Quyidagi kod nima chiqaradi?
```python
i = 0
while i < 3:
    i += 1
print(i)
```
+ 3
- 2
- 4
- 0
> Sikl i < 3 yolg'on bo'lguncha aylanadi — i 3 ga teng bo'lganda to'xtaydi.

? Quyidagi kod nima chiqaradi?
```python
nums = [10, 20, 30]
nums.append(40)
print(len(nums))
```
+ 4
- 3
- 40
- [10, 20, 30, 40]
> append() ro'yxat oxiriga element qo'shadi: endi 4 ta element.

? Quyidagi kod nima chiqaradi?
```python
user = {"ism": "Ali", "yosh": 20}
print(user["ism"])
```
+ Ali
- ism
- {"ism": "Ali"}
- 20
> Lug'atdan qiymat kalit orqali olinadi: user["ism"] — "Ali".

? Quyidagi kod nima chiqaradi?
```python
def kvadrat(n):
    return n * n

print(kvadrat(4))
```
+ 16
- 8
- 4
- None
> Funksiya n * n ni qaytaradi: 4 * 4 = 16.

? Quyidagi kod qanday natija beradi?
```python
yosh = 20
print("Yoshim: " + yosh)
```
+ TypeError — matnga sonni + bilan qo'shib bo'lmaydi
- SyntaxError — qavs yopilmagan
- NameError — o'zgaruvchi topilmadi
- Xatosiz chiqadi: Yoshim: 20
> str + int mumkin emas. To'g'risi: "Yoshim: " + str(yosh) yoki f"Yoshim: {yosh}".

? Funksiyani vazifasiga moslang:
len() :: uzunlikni topadi
input() :: foydalanuvchidan ma'lumot oladi
int() :: butun songa o'giradi
print() :: ekranga chiqaradi

? Qatorlarni tartibga qo'ying: dastur yoshni so'raydi va unga 1 qo'shib chiqaradi.
1. yosh = input("Yoshingiz: ")
2. yosh = int(yosh)
3. yosh = yosh + 1
4. print(yosh)
"""


def python() -> Course:
    found = Course.objects.filter(slug=COURSE_SLUG).first()
    if found is None:
        raise SystemExit(f"«{COURSE_SLUG}» kursi topilmadi: avval Python kursini yarating.")
    return found


@transaction.atomic
def setup() -> None:
    course = python()
    service, created = Course.objects.get_or_create(
        slug=SERVICE_SLUG,
        defaults={
            "title": "Daraja testlari (xizmat kursi)",
            "short_description": (
                "Botdagi daraja testlari savollari. Nashr qilmang va hech kimni yozmang."
            ),
            "category": course.category,
            "status": Course.Status.DRAFT,
        },
    )
    if not created and service.status == Course.Status.PUBLISHED:
        raise SystemExit("Xizmat kursi nashr qilingan — admin'da «Qoralama»ga qaytaring.")
    module, _ = Module.objects.get_or_create(course=service, title=TITLE, defaults={"order": 1})
    lesson, _ = Lesson.objects.get_or_create(
        module=module, title=f"{TITLE}: daraja testi", defaults={"order": 1}
    )
    quiz, _ = Quiz.objects.get_or_create(
        lesson=lesson, defaults={"title": f"{TITLE}: daraja testi"}
    )
    if not quiz.questions.exists():
        import_questions(quiz, parse(QUESTIONS))
    test, made = PlacementTest.objects.get_or_create(
        course=course,
        title=TITLE,
        defaults={"quiz": quiz, "questions_count": 12, "duration_min": 15, "is_active": True},
    )
    state = "yaratildi" if made else "avvaldan bor (o'zgartirilmadi)"
    active = "faol" if test.is_active else "o'chirilgan"
    print(f"Xizmat kursi: {service.title} (id {service.pk}, {service.get_status_display()})")
    print(f"Savollar banki: {quiz.questions.count()} ta")
    print(
        f"Daraja testi «{test.title}» {state}: {test.questions_count} savol, "
        f"{test.duration_min} daqiqa, {active}; natija va ariza — «{course.title}» kursi bo'yicha"
    )


def status() -> None:
    attempts = PlacementAttempt.objects.filter(finished_at__isnull=False)
    summary = attempts.aggregate(count=Count("pk"), people=Count("user", distinct=True))
    average = attempts.aggregate(value=Avg("score"))["value"]
    coupons = attempts.filter(coupon__isnull=False)
    print(
        f"Tugatilgan: {summary['count']} ta ({summary['people']} kishi), o'rtacha natija: "
        f"{round(average) if average is not None else '—'}%"
    )
    by_percent = coupons.values("coupon__percent").annotate(count=Count("pk"))
    used = coupons.filter(coupon__used_at__isnull=False).count()
    gave = ", ".join(f"{row['coupon__percent']}% — {row['count']} ta" for row in by_percent)
    print(f"Kuponlar: {gave or '—'}; ishlatilgan: {used}")
    sources = (
        attempts.values("user__signup_source")
        .annotate(count=Count("user", distinct=True))
        .order_by("-count")
    )
    direct = "to'g'ridan"
    came = [f"{row['user__signup_source'] or direct} — {row['count']}" for row in sources]
    print(f"Manbalar: {', '.join(came) or '—'}")
    running = PlacementAttempt.objects.filter(finished_at__isnull=True).count()
    if running:
        print(f"Hozir ishlayapti: {running}")
    print("\nOxirgi 15 ta:")
    latest = attempts.select_related("user", "test", "coupon").order_by("-finished_at")[:15]
    for item in latest:
        user = item.user
        name = f"{user.first_name} {user.last_name}".strip() or "(ismsiz)"
        coupon = f"{item.coupon.percent}%" if item.coupon else "—"
        print(
            f"  {item.finished_at:%d.%m %H:%M}  {name[:24]:24} {user.phone}  "
            f"{item.test.title}: {item.score}%  kupon {coupon}  {user.signup_source or ''}"
        )


def switch(active: bool) -> None:
    changed = PlacementTest.objects.filter(course=python(), title=TITLE).update(is_active=active)
    if not changed:
        raise SystemExit("Daraja testi topilmadi: avval ACTION=setup.")
    print("Daraja testi " + ("yoqildi" if active else "o'chirildi (botda tugma ko'rinmaydi)"))


if ACTION == "setup":
    setup()
elif ACTION == "status":
    status()
elif ACTION in ("on", "off"):
    switch(ACTION == "on")
else:
    raise SystemExit(f"Noma'lum ACTION={ACTION}: setup, status, on yoki off.")
