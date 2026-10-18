"""Python guruhi, 7-mavzu: list, tuple, dict va set — test (15 savol) va 5 ta amaliy topshiriq,
AI tekshiruvi, Telegram'da hisobot va muddatida bajarmaganlarga jarima.

Serverda, /srv/sifatedu papkasida (kod Django shell'ga uzatiladi, image qayta yig'ilmaydi):

  S=backend/scripts/vazifa_python_7mavzu.py
  dc exec -T -e ACTION=send   backend python manage.py shell < $S
  dc exec -T -e ACTION=status backend python manage.py shell < $S
  dc exec -T -e ACTION=finish backend python manage.py shell < $S

send   — «Python asoslari» moduliga 7-mavzu darsi: test (15 savol) va uy vazifasi (5 ta amaliy
         topshiriq, muddat — bugun UNTIL, standart 23:00). Dars «Python» guruhi uchun ochiladi,
         har o'quvchiga botda xabar: «Testni boshlash» tugmasi va vazifa sahifasi havolasi.
         Qayta ishga tushirsa, mavjudini o'zgartirmaydi va xabarni takror yubormaydi.
status — kim test ishladi (natija), kim amaliyotni yubordi; yuborilgan kodni AI (Gemini)
         5 ta topshiriq bo'yicha tekshiradi (har javob bir marta — natija 7 kun eslab qolinadi).
         Hisobot direktor va adminlarga Telegram'da (kunlik hisobot boradigan hisoblar) va shu
         yerda chiqadi. Istalgan vaqtda ishga tushirish mumkin.
finish — muddat tugagach: hisobot va jarima. Testni muddatida ishlamaganga va amaliyotni
         muddatida yubormaganga — har biri uchun XP (XP=..., standart — sozlamalardagi «uy vazifasi
         muddatidan kechikdi» qiymati), o'quvchiga botda qisqa xabar. Qayta ishga tushirsa,
         ikkinchi marta yechilmaydi. Muddatdan keyin yuborilgan vazifaga avtomatik «kechikdi»
         jarimasi bilan bir xil yozuv — ikkalasi birga yechilmaydi. FORCE=1 — muddatdan oldin.

AI bahosi faqat hisobot uchun, o'quvchiga bormaydi; rasmiy baho — o'qituvchi kabinetida
(«Tekshirish»). Jarimani o'qituvchi yoki admin bekor qila oladi (guruh sahifasi → jarimalar).
"""

import json
import os
from datetime import datetime
from html import escape, unescape
from pathlib import Path
from typing import Any, Literal, NamedTuple

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from google import genai
from google.genai import types
from pydantic import BaseModel

from apps.catalog.models import Course, Lesson, Module
from apps.homework.models import Assignment, Submission, SubmissionFile
from apps.learning.models import StudyGroup
from apps.live.models import GroupLesson
from apps.live.services import members
from apps.notifications import telegram
from apps.notifications.models import Notification
from apps.notifications.services import can_message, notify, telegram_accounts
from apps.notifications.texts import day_month
from apps.quizzes.models import Attempt, Quiz
from apps.quizzes.parser import parse
from apps.quizzes.services import import_questions
from apps.rewards import services as rewards
from apps.rewards.models import Entry
from apps.stats.report import recipients
from apps.users.models import User

ACTION = os.environ.get("ACTION", "status")
COURSE_SLUG = os.environ.get("COURSE", "python")
GROUP_NAME = os.environ.get("GROUP", "Python")
UNTIL = os.environ.get("UNTIL", "23:00")
MODULE = "Python asoslari"
TITLE = "7-mavzu: list, tuple, dict va set"
SHORT = "list, tuple, dict va set"
HOMEWORK_TITLE = "Amaliyot: list, tuple, dict va set (5 ta topshiriq)"
CACHE_KEY = "vazifa7:ai:{}"
CACHE_SECONDS = 7 * 24 * 3600
TELEGRAM_CHUNK = 3800
MAX_FILE = 5 * 1024 * 1024
MAX_CHARS = 60_000
MAX_IMAGES = 4
TEXT_FILES = {".py", ".txt", ".md", ".ipynb"}
IMAGES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
MARKS = {"correct": "✅", "partial": "🟡", "wrong": "❌", "missing": "➖"}
POINTS = {"correct": 100, "partial": 50, "wrong": 0, "missing": 0}

QUESTIONS = r"""
? Qaysi biri kortej (tuple)?
+ (1, 2, 3)
- [1, 2, 3]
- {1, 2, 3}
- {"a": 1}
> Kortej oddiy qavs bilan yoziladi; [] — ro'yxat, {1, 2} — to'plam, {"a": 1} — lug'at.

? Quyidagi kod nima bo'ladi?
```python
t = (10, 20, 30)
t[0] = 5
print(t)
```
+ Xato beradi (TypeError)
- (5, 20, 30)
- (10, 20, 30)
- (5, 10, 20, 30)
> Kortej o'zgarmas: elementini almashtirib bo'lmaydi.

? Bitta elementli kortej qanday yoziladi?
+ (5,)
- (5)
- [5]
- {5}
> (5) — oddiy son; vergul qo'yilsa, kortej bo'ladi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
x, y = (4, 9)
print(y - x)
```
= 5
> Kortej ochiladi: x = 4, y = 9.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
a = [1, 2]
a.append([3, 4])
print(len(a))
```
= 3
> append() ro'yxatni bitta element qilib qo'shadi: [1, 2, [3, 4]].

? Quyidagi kod nima chiqaradi?
```python
narx = {"olma": 12000, "non": 4000}
print(narx["non"])
```
+ 4000
- non
- 12000
- Xato beradi
> Lug'atdan qiymat kalit orqali olinadi.

? Quyidagi kod nima chiqaradi?
```python
d = {"a": 1}
d["b"] = 2
print(d)
```
+ {'a': 1, 'b': 2}
- {'a': 1}
- {'b': 2}
- Xato beradi
> Yangi kalitga qiymat berilsa, u lug'atga qo'shiladi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
d = {"ali": 5, "vali": 4}
print(d.get("hasan", 0))
```
= 0
> get() kalit topilmasa, ikkinchi qiymatni qaytaradi.

? Quyidagi kod nima bo'ladi?
```python
d = {"ali": 5}
print(d["vali"])
```
+ KeyError xatosi
- None
- 0
- vali
> Lug'atda yo'q kalit [] bilan so'ralsa — KeyError. Xatosiz olish uchun get() bor.

? Quyidagi kod nima chiqaradi?
```python
d = {"olma": 3, "anor": 5}
print(5 in d)
```
+ False
- True
- 5
- Xato beradi
> in lug'atda kalitlarni tekshiradi, qiymatlarni emas.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
d = {"x": 1, "y": 2, "z": 3}
print(sum(d.values()))
```
= 6
> values() — qiymatlar: 1 + 2 + 3 = 6.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
s = set([1, 2, 2, 3, 3, 3])
print(len(s))
```
= 3
> To'plamda takrorlanuvchi element bo'lmaydi: {1, 2, 3}.

? Bo'sh to'plam (set) qanday yaratiladi?
+ set()
- {}
- []
- ()
> {} — bo'sh lug'at (dict); bo'sh to'plam faqat set() bilan yaratiladi.

? Quyidagi kod nima chiqaradi?
```python
a = {1, 2, 3}
b = {2, 3, 4}
print(a & b)
```
+ {2, 3}
- {1, 2, 3, 4}
- {1, 4}
- {1}
> & — ikkala to'plamda ham bor elementlar (kesishma).

? Qaysi turlarga element qo'shish yoki o'chirish mumkin? Bir nechta javob.
+ list
+ dict
+ set
- tuple
> Faqat kortej (tuple) o'zgarmas.
"""

TASKS = [
    """1-topshiriq. Ro'yxat (list): baholar jurnali
baholar = [5, 3, 4, 5, 2, 4]
1) baholar sonini chiqaring (len);
2) eng yuqori va eng past bahoni chiqaring (max, min);
3) o'rtacha bahoni 2 xonagacha yaxlitlab chiqaring (sum, len, round);
4) 5 baho necha marta borligini chiqaring (count);
5) ro'yxatga yangi 4 bahoni qo'shing (append), kamayish tartibida saralang
   (sort(reverse=True)) va ro'yxatni chiqaring;
6) eng yaxshi 3 ta bahoni kesim bilan chiqaring ([:3]).

Kutilgan natija:
Baholar soni: 6
Eng yuqori: 5
Eng past: 2
O'rtacha: 3.83
5 lar soni: 2
Saralangan: [5, 5, 4, 4, 4, 3, 2]
Eng yaxshi 3 tasi: [5, 5, 4]""",
    """2-topshiriq. Kortej (tuple): hafta kunlari
hafta = ("Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba")
1) birinchi va oxirgi kunni chiqaring (indeks 0 va -1);
2) kunlar sonini chiqaring (len);
3) "Juma" nechanchi indeksda ekanini chiqaring (index);
4) ish kunlarini — birinchi 5 tasini kesim bilan chiqaring ([:5]);
5) "Shanba" kortejda bormi — tekshirib chiqaring (in);
6) nuqta = (3, 7) kortejini ikki o'zgaruvchiga oching (x, y = nuqta) va x + y, x * y ni
   chiqaring;
7) kortejni nega o'zgartirib bo'lmasligini bitta izoh (#) bilan yozing.

Kutilgan natija:
Birinchi: Dushanba
Oxirgi: Yakshanba
Kunlar soni: 7
Juma indeksi: 4
Ish kunlari: ('Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma')
Shanba bormi: True
x + y = 10
x * y = 21""",
    """3-topshiriq. Lug'at (dict): do'kon narxlari
narxlar = {"olma": 12000, "non": 4000, "sut": 9000}
1) nonning narxini chiqaring;
2) "choy" ni 15000 narx bilan qo'shing;
3) non narxini 4500 ga o'zgartiring;
4) "sut" ni o'chiring (pop yoki del) va lug'atni chiqaring;
5) mahsulotlar sonini chiqaring (len);
6) barcha narxlar yig'indisini chiqaring (sum va values());
7) "shakar" narxini get() bilan oling: bo'lmasa 0 chiqsin;
8) eng qimmat narxni chiqaring (max va values()).

Kutilgan natija:
Non: 4000
{'olma': 12000, 'non': 4500, 'choy': 15000}
Mahsulotlar soni: 3
Jami: 31500
Shakar: 0
Eng qimmat narx: 15000""",
    """4-topshiriq. To'plam (set): ikki to'garak
python = {"Ali", "Vali", "Hasan", "Olim", "Zarina"}
dizayn = {"Vali", "Zarina", "Sardor", "Madina"}
To'plam har safar boshqa tartibda chiqishi mumkin, shuning uchun ro'yxatlarni sorted() bilan
tartiblab chiqaring.
1) ikkala to'garakka ham qatnashadiganlar (&);
2) hamma o'quvchilar, takrorlanmasdan (|);
3) faqat Python'ga qatnashadiganlar (-);
4) jami nechta turli o'quvchi borligi (len);
5) dizayn to'plamiga "Ali" ni qo'shing (add) va Ali endi ikkala to'garakda ham bormi —
   tekshirib chiqaring (in va and).

Kutilgan natija:
Ikkalasida: ['Vali', 'Zarina']
Hammasi: ['Ali', 'Hasan', 'Madina', 'Olim', 'Sardor', 'Vali', 'Zarina']
Faqat Python: ['Ali', 'Hasan', 'Olim']
Jami o'quvchilar: 7
Ali ikkalasida: True""",
    """5-topshiriq. Hammasi birga: sinf sardori saylovi
ovozlar = ["Ali", "Vali", "Ali", "Hasan", "Vali", "Ali"]
1) nomzodlarni takrorlanmasdan, alifbo tartibida chiqaring (set va sorted);
2) natija lug'atini tuzing: har nomzodning ovozlari soni count() bilan, kalitlar tartibi —
   Ali, Vali, Hasan; lug'atni chiqaring;
3) eng ko'p ovoz sonini chiqaring (max va values());
4) jami ovozlar sonini chiqaring (len) va lug'atdagi ovozlar yig'indisi unga tengligini
   tekshiring (sum(...) == len(...));
5) g'olibni if / elif / else bilan toping: kimning ovozi eng ko'p ovozga teng;
6) g'olib va uning ovozini kortejga yig'ing, so'ng kortejni ochib (nom, son = ...) chiqaring.

Kutilgan natija:
Nomzodlar: ['Ali', 'Hasan', 'Vali']
Natija: {'Ali': 3, 'Vali': 2, 'Hasan': 1}
Eng ko'p ovoz: 3
Jami ovozlar: 6
Tekshiruv: True
G'olib: Ali — 3 ovoz""",
]

INSTRUCTIONS = (
    "5 ta topshiriq — hammasini bitta kodda yuboring: pastdagi «Kod» maydoniga qo'ying (yoki .py "
    "fayl biriktiring). Har topshiriq oldidan izoh yozing: # 1-topshiriq, # 2-topshiriq va h.k.\n"
    "Yuborishdan oldin kodni ishga tushirib, natijani «Kutilgan natija» bilan solishtiring: "
    "yozuvlar biroz farq qilsa bo'ladi, qiymatlar aynan shunday bo'lsin. Javobni qo'lda yozmang "
    "(print(31500) emas) — hisoblashni kod qilsin. Sikl (for, while) shart emas.\n\n"
    + "\n\n".join(TASKS)
)

SYSTEM = """Sen Python o'qituvchisisan. Boshlovchi o'quvchining uy vazifasini tekshirasan: 5 ta
topshiriq, har birida «Kutilgan natija» bor. Kodni ishga tushirmaysan — uni xayolan qatorma-qator
bajarib, nima chiqarishini aniqlaysan.

Har topshiriq uchun holat:
- "correct" — kod xatosiz ishlaydi, barcha qiymatlar kutilgan natija bilan bir xil va kod ularni
  o'zi hisoblaydi. Yozuvlar (masalan «Jami:») va bo'shliqlar farq qilsa ham bo'ladi.
- "partial" — bir qismi to'g'ri: ba'zi qiymatlar xato yoki yetishmaydi, yoki so'ralgan usul
  (masalan sorted(), get(), if/elif) ishlatilmagan.
- "wrong" — urinib ko'rilgan, lekin natija noto'g'ri, kod xato beradi yoki javob qo'lda yozilgan
  (masalan print(31500) — hisoblanmagan).
- "missing" — bu topshiriq uchun kod yo'q.

Kod qaysi topshiriqqa tegishli ekanini izohlar (# 1-topshiriq) va o'zgaruvchi nomlaridan aniqla.
Har topshiriqni alohida bahola, go'yo u alohida ishga tushirilgandek. Biror qator xato berib
dasturni to'xtatsa, o'sha topshiriq — ko'pi bilan "partial", buni izohda ayt.
Rasm yuborilgan bo'lsa (kod yoki natija skrinshoti), undagi kodni o'qib bahola.

"number" — topshiriq raqami (1–5), har biri uchun bitta yozuv. "note" — o'zbekcha, lotin
yozuvida, 120 belgigacha: nima xato yoki nima yetishmaydi. To'g'ri bo'lsa — bo'sh qator.
"""


class TaskCheck(BaseModel):
    number: int
    status: Literal["correct", "partial", "wrong", "missing"]
    note: str


class Review(BaseModel):
    tasks: list[TaskCheck]


class Row(NamedTuple):
    user: User
    first: int | None  # birinchi tugatilgan urinish (%)
    best: int | None
    quiz_on_time: bool
    submission: Submission | None
    homework_on_time: bool
    review: dict[str, Any] | None


# --- Umumiy ---


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


def name_of(user: User) -> str:
    return f"{user.first_name} {user.last_name}".strip() or user.phone


def moment(value: datetime) -> str:
    local = timezone.localtime(value)
    return f"{day_month(local.date(), 'uz')}, {local:%H:%M}"


def penalty_xp() -> int:
    raw = os.environ.get("XP", "").strip()
    return int(raw) if raw else rewards.settings().homework_late_penalty


def lesson_link(python: Course, lesson: Lesson) -> str:
    return f"/dashboard/courses/{python.slug}/lessons/{lesson.pk}#homework"


def existing() -> tuple[StudyGroup, Lesson, Quiz, Assignment]:
    python = course()
    team = group(python)
    lesson = Lesson.objects.filter(module__course=python, title=TITLE).first()
    quiz = Quiz.objects.filter(lesson=lesson).first() if lesson else None
    assignment = Assignment.objects.filter(lesson=lesson).first() if lesson else None
    if lesson is None or quiz is None or assignment is None:
        raise SystemExit("Vazifa hali yuborilmagan: avval ACTION=send.")
    return team, lesson, quiz, assignment


# --- send ---


def deadline_today() -> datetime:
    hours, minutes = (int(part) for part in UNTIL.split(":"))
    now = timezone.localtime()
    until = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
    if until <= now:
        raise SystemExit(
            f"Muddat ({UNTIL}) o'tib ketgan: kechroq vaqt bering, masalan UNTIL=23:30."
        )
    return until


@transaction.atomic
def prepare() -> tuple[StudyGroup, Lesson, Quiz, Assignment, GroupLesson]:
    python = course()
    team = group(python)
    module, _created = Module.objects.get_or_create(
        course=python, title=MODULE, defaults={"order": 1}
    )
    lesson = Lesson.objects.filter(module=module, title=TITLE).first()
    if lesson is None:
        last = module.lessons.order_by("-order").values_list("order", flat=True).first() or 0
        lesson = Lesson.objects.create(module=module, title=TITLE, order=last + 1)
    quiz, _created = Quiz.objects.get_or_create(
        lesson=lesson, defaults={"title": f"{TITLE} — test"}
    )
    if not quiz.questions.exists():
        import_questions(quiz, parse(QUESTIONS))
    assignment = Assignment.objects.filter(lesson=lesson).first()
    if assignment is None:
        assignment = Assignment.objects.create(
            lesson=lesson,
            title=HOMEWORK_TITLE,
            instructions=INSTRUCTIONS,
            deadline=deadline_today(),
        )
    record, _created = GroupLesson.objects.get_or_create(
        group=team, lesson=lesson, defaults={"opened_by": team.teacher}
    )
    return team, lesson, quiz, assignment, record


def send() -> None:
    team, lesson, quiz, assignment, record = prepare()
    python = team.course
    until = moment(assignment.deadline) if assignment.deadline else "—"
    xp = penalty_xp()
    count = quiz.questions.count()
    body = (
        f"1) Test — {count} ta savol, shu yerda: «Testni boshlash» tugmasi.\n"
        f"2) Amaliyot — {len(TASKS)} ta topshiriq: «Ochish» → dars sahifasidagi «Uy vazifasi», "
        "kodni o'sha yerga yuboring.\n\n"
        f"Muddat: {until}. Bajarmaganlarga jarima: test uchun −{xp} XP, amaliyot uchun −{xp} XP."
    )
    people = list(members(team.pk))
    accounts = telegram_accounts([user.pk for user in people])
    sent = repeated = 0
    unreachable = []
    for user in people:
        created = notify(
            user,
            Notification.Kind.LESSON_OPENED,
            title=f"Bugungi vazifa: {SHORT}",
            body=body,
            link=lesson_link(python, lesson),
            dedupe_key=f"lesson-open:{record.pk}:{user.pk}",
            quiz_id=quiz.pk,
        )
        if created is None:
            repeated += 1
        else:
            sent += 1
        if not can_message(accounts.get(user.pk)):
            unreachable.append(user)
    print(f"Dars: {lesson.title} (id {lesson.pk}), test — {count} savol")
    print(f"Amaliyot: {len(TASKS)} ta topshiriq, muddat — {until}, jarima — −{xp} XP har biri")
    print(f"Guruh «{team.name}»: {len(people)} o'quvchi; xabar yuborildi — {sent}", end="")
    print(f", avval yuborilgan — {repeated}" if repeated else "")
    if unreachable:
        print("Telegram'i ulanmagan yoki botni to'xtatgan (xabar faqat saytda):")
        for user in unreachable:
            print(f"  {name_of(user)[:30]:30} {user.phone}")


# --- AI tekshiruv ---


def read_file(item: SubmissionFile) -> bytes:
    with item.file.open("rb") as handle:
        return handle.read(MAX_FILE + 1)


def notebook_code(data: bytes) -> str:
    """Jupyter/Colab: faqat kod kataklari."""
    cells = json.loads(data.decode("utf-8", errors="replace")).get("cells", [])
    blocks = []
    for cell in cells:
        if cell.get("cell_type") == "code":
            source = cell.get("source", "")
            blocks.append("".join(source) if isinstance(source, list) else str(source))
    return "\n\n".join(blocks)


def answer_parts(submission: Submission) -> list[types.Part]:
    lines = ["TOPSHIRIQLAR:", "\n\n".join(TASKS), "", "O'QUVCHI JAVOBI:"]
    if submission.text:
        lines += ["Izoh:", submission.text]
    if submission.link:
        lines.append(f"Havola (ochilmaydi): {submission.link}")
    if submission.code:
        lines += ["Kod:", "```python", submission.code, "```"]
    images: list[types.Part] = []
    for item in submission.files.all():
        suffix = Path(item.name).suffix.lower()
        if item.size > MAX_FILE or (suffix not in TEXT_FILES and suffix not in IMAGES):
            lines.append(f"Fayl {item.name} — o'qib bo'lmadi")
            continue
        data = read_file(item)
        if suffix in IMAGES:
            if len(images) < MAX_IMAGES:
                images.append(types.Part.from_bytes(data=data, mime_type=IMAGES[suffix]))
                lines.append(f"Rasm {item.name} — ilova qilingan")
            continue
        try:
            content = notebook_code(data) if suffix == ".ipynb" else data.decode("utf-8", "replace")
        except ValueError:
            content = data.decode("utf-8", "replace")
        lines += [f"Fayl {item.name}:", "```", content, "```"]
    return [types.Part.from_text(text="\n".join(lines)[:MAX_CHARS]), *images]


def call_model(submission: Submission) -> Review:
    client = genai.Client(
        api_key=settings.GEMINI_API_KEY, http_options=types.HttpOptions(timeout=180_000)
    )
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=types.Content(role="user", parts=answer_parts(submission)),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM,
            response_mime_type="application/json",
            response_schema=Review,
            max_output_tokens=16_000,
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel("MEDIUM")),
        ),
    )
    parsed = response.parsed
    if isinstance(parsed, Review):
        return parsed
    return Review.model_validate_json(response.text or "")


def summarize(review: Review) -> dict[str, Any]:
    """Har topshiriq holati (raqam tartibida), xatolar izohi va 0–100 baho."""
    found = {task.number: task for task in review.tasks}
    marks: list[str] = []
    notes: dict[int, str] = {}
    for number in range(1, len(TASKS) + 1):
        task = found.get(number)
        status = task.status if task else "missing"
        marks.append(status)
        if task and status != "correct" and task.note.strip():
            notes[number] = " ".join(task.note.split())[:160]
    score = round(sum(POINTS[mark] for mark in marks) / len(marks))
    return {"marks": marks, "notes": notes, "score": score}


def ai_review(submission: Submission) -> dict[str, Any] | None:
    """Javobning AI bahosi (bir marta; keyingi safar keshdan). Kalit bo'lmasa — None."""
    if not settings.GEMINI_API_KEY:
        return None
    key = CACHE_KEY.format(submission.pk)
    found: dict[str, Any] | None = cache.get(key)
    if found is not None:
        return found
    print(f"  AI tekshirmoqda: {name_of(submission.student)}…")
    try:
        data = summarize(call_model(submission))
    except Exception as exc:
        print(f"  ! AI tekshira olmadi: {exc}")
        return {"error": str(exc)[:200]}
    cache.set(key, data, CACHE_SECONDS)
    return data


# --- Natijalar ---


def collect(team: StudyGroup, quiz: Quiz, assignment: Assignment) -> list[Row]:
    deadline = assignment.deadline
    rows = []
    for user in members(team.pk):
        attempts = list(
            Attempt.objects.filter(quiz=quiz, student=user, finished_at__isnull=False).order_by(
                "finished_at"
            )
        )
        scores = [attempt.score or 0 for attempt in attempts]
        quiz_on_time = any(
            attempt.finished_at is not None
            and (deadline is None or attempt.finished_at <= deadline)
            for attempt in attempts
        )
        sent = list(
            Submission.objects.filter(assignment=assignment, student=user).order_by("attempt")
        )
        latest = sent[-1] if sent else None
        rows.append(
            Row(
                user=user,
                first=scores[0] if scores else None,
                best=max(scores) if scores else None,
                quiz_on_time=quiz_on_time,
                submission=latest,
                homework_on_time=any(
                    deadline is None or item.created_at <= deadline for item in sent
                ),
                review=ai_review(latest) if latest else None,
            )
        )
    return rows


def missed(row: Row) -> list[str]:
    return [
        part
        for part, done in (("test", row.quiz_on_time), ("amaliyot", row.homework_on_time))
        if not done
    ]


def rank(row: Row) -> tuple[int, int, str]:
    review = row.review or {}
    homework = review.get("score", 0) if row.submission else -1
    return (-homework, -(row.best if row.best is not None else -1), name_of(row.user))


def quiz_text(row: Row) -> str:
    if row.first is None:
        return "test —"
    late = "" if row.quiz_on_time else " (kechikdi)"
    if row.best is not None and row.best > row.first:
        return f"test {row.first}% → {row.best}%{late}"
    return f"test {row.first}%{late}"


def homework_text(row: Row) -> tuple[str, str]:
    """(asosiy qism, xatolar izohi)."""
    submission = row.submission
    if submission is None:
        return "amaliyot yubormadi", ""
    parts = ["amaliyot"]
    review = row.review
    notes = ""
    if review is None:
        parts.append("yubordi")
    elif "error" in review:
        parts.append("yubordi (AI tekshira olmadi)")
    else:
        parts.append(f"{review['score']} {''.join(MARKS[mark] for mark in review['marks'])}")
        notes = " · ".join(f"{number}) {note}" for number, note in review["notes"].items())
    if not row.homework_on_time:
        parts.append("(kechikdi)")
    if submission.status == Submission.Status.ACCEPTED:
        parts.append(f"· ustoz: {submission.score}")
    elif submission.status == Submission.Status.CHANGES_REQUESTED:
        parts.append("· ustoz qaytardi")
    return " ".join(parts), notes


def report(
    rows: list[Row], team: StudyGroup, quiz: Quiz, assignment: Assignment, *, final: bool
) -> list[str]:
    """Telegram uchun qatorlar (HTML)."""
    total = len(rows)
    tested = [row for row in rows if row.first is not None]
    sent = [row for row in rows if row.submission is not None]
    scored = [row.review["score"] for row in sent if row.review and "score" in row.review]
    until = moment(assignment.deadline) if assignment.deadline else "—"
    lines = [
        f"📋 <b>{escape(team.name, quote=False)} · {escape(SHORT, quote=False)}</b>",
        f"Muddat: {until} · o'quvchilar: {total} · holat: {timezone.localtime():%H:%M}",
        "",
        f"📝 Test ({quiz.questions.count()} savol): ishladi <b>{len(tested)}/{total}</b>"
        + (
            f", o'rtacha {round(sum(row.first or 0 for row in tested) / len(tested))}%"
            if tested
            else ""
        ),
        f"💻 Amaliyot ({len(TASKS)} ta): yubordi <b>{len(sent)}/{total}</b>"
        + (f", AI bahosi o'rtacha {round(sum(scored) / len(scored))}/100" if scored else ""),
    ]
    if not settings.GEMINI_API_KEY:
        lines.append("AI tekshiruvi o'chiq (GEMINI_API_KEY yo'q) — amaliyotni ustoz tekshiradi.")
    lines.append("")
    for number, row in enumerate(sorted(rows, key=rank), 1):
        work, notes = homework_text(row)
        lines.append(
            f"{number}. {escape(name_of(row.user), quote=False)} — {quiz_text(row)} · {work}"
        )
        if notes:
            lines.append(f"    {escape(notes, quote=False)}")
    lazy = [row for row in rows if missed(row)]
    if lazy:
        lines.append("")
        if final:
            lines.append(
                f"⛔ <b>Jarima</b> ({len(lazy)} kishi, har qism uchun −{penalty_xp()} XP):"
            )
        else:
            lines.append(f"⏳ <b>Hali bajarmagan</b> ({len(lazy)} kishi):")
        lines.extend(
            f"• {escape(name_of(row.user), quote=False)} — {', '.join(missed(row))}"
            for row in sorted(lazy, key=lambda row: name_of(row.user))
        )
    elif rows:
        lines += ["", "✅ Hamma bajardi."]
    if sent:
        lines += ["", "Rasmiy baho — saytda: «Tekshirish» bo'limi."]
    return lines


def chunks(lines: list[str]) -> list[str]:
    parts: list[str] = []
    current = ""
    for line in lines:
        if current and len(current) + len(line) + 1 > TELEGRAM_CHUNK:
            parts.append(current)
            current = ""
        current = f"{current}\n{line}" if current else line
    if current:
        parts.append(current)
    return parts


def plain(line: str) -> str:
    return unescape(line.replace("<b>", "").replace("</b>", ""))


def deliver(lines: list[str]) -> None:
    """Hisobot — shu yerda va Telegram'da (kunlik hisobot oluvchilar: direktor va adminlar)."""
    print()
    for line in lines:
        print(plain(line))
    print()
    accounts = recipients()
    if not settings.TELEGRAM_BOT_TOKEN or not accounts:
        print("! Telegram'da hech kimga yuborilmadi: admin/direktor hisobi botga ulanmagan.")
        return
    reached = 0
    for account in accounts:
        try:
            for part in chunks(lines):
                telegram.send_message(account.uid, part)
        except (telegram.TelegramError, telegram.TelegramNotConfiguredError, OSError) as exc:
            print(f"  ! {account.uid}: {exc}")
        else:
            reached += 1
    print(f"Hisobot Telegram'da {reached} kishiga yuborildi.")


def status() -> None:
    team, _lesson, quiz, assignment = existing()
    deliver(report(collect(team, quiz, assignment), team, quiz, assignment, final=False))


def punish(row: Row, quiz: Quiz, assignment: Assignment, xp: int) -> list[str]:
    """Muddatida bajarilmagan har qism uchun jarima. Qaytadi: shu safar yechilgan qismlar."""
    user_id = row.user.pk
    course_id = assignment.lesson.module.course_id
    # Amaliyot kaliti — avtomatik «kechikdi» jarimasiniki: kechikib yuborsa ham bittasi qoladi.
    wanted = {
        "test": (f"quiz-missed:{user_id}:{quiz.pk}", f"Test ishlanmadi: {SHORT}"),
        "amaliyot": (
            f"homework-late:{user_id}:{assignment.pk}",
            f"Amaliyot muddatida topshirilmadi: {SHORT}",
        ),
    }
    new = []
    for part in missed(row):
        key, note = wanted[part]
        entry = rewards.penalize(
            user_id, Entry.Reason.HOMEWORK_LATE, xp, key=key, course_id=course_id, note=note
        )
        if entry is not None:
            new.append(part)
    return new


def finish() -> None:
    team, lesson, quiz, assignment = existing()
    if (
        assignment.deadline
        and timezone.now() < assignment.deadline
        and os.environ.get("FORCE") != "1"
    ):
        raise SystemExit(
            f"Muddat hali tugamagan ({moment(assignment.deadline)}). Hozircha ACTION=status."
        )
    rows = collect(team, quiz, assignment)
    xp = penalty_xp()
    created = 0
    for row in rows:
        new = punish(row, quiz, assignment, xp)
        if not new:
            continue
        created += len(new)
        notify(
            row.user,
            Notification.Kind.REWARD,
            title=f"Jarima: −{xp * len(new)} XP",
            body=(
                f"«{SHORT}» vazifasi muddatida bajarilmadi: {', '.join(new)}. "
                "Kechikib bo'lsa ham topshiring — ustoz ko'rib chiqadi."
            ),
            link=lesson_link(team.course, lesson),
            dedupe_key=f"vazifa7-penalty:{assignment.pk}:{row.user.pk}",
        )
    print(f"Yangi jarima yozuvlari: {created}")
    deliver(report(rows, team, quiz, assignment, final=True))


ACTIONS = {"send": send, "status": status, "finish": finish}
if ACTION not in ACTIONS:
    raise SystemExit(f"ACTION: {', '.join(ACTIONS)}")
ACTIONS[ACTION]()
