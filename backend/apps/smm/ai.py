"""Gemini: haftalik reja va har post mazmuni (tuzilgan JSON javob).

Formulalar raqobatchilar tahlilidan (docs/raqobatchilar-tahlili.md): eng ko'p ko'rilgan videolar
ota-onaning xavotiri yoki g'ururi haqidagi hikoya — muammo → burilish → g'urur → yumshoq taklif.
"""

import logging
from decimal import Decimal

from django.conf import settings
from django.utils.timezone import localtime
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel

from apps.catalog.models import Course

from .models import Post, SmmSettings

logger = logging.getLogger(__name__)

# Gemini bu muddatni server tomonda ham qo'llaydi (504 DEADLINE_EXCEEDED); vazifa chegarasi 200 s.
TIMEOUT_MS = 170_000
MILLION = Decimal(1_000_000)


WEEKDAYS = ("Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba")


class AiError(Exception):
    """AI javob bermadi yoki javobi yaroqsiz."""


FORMULAS = {
    Post.Formula.FAMILY: (
        "Oilaviy mini-sahna (45–60 soniyalik video ssenariysi, uyda suratga olinadi). Tuzilishi: "
        "1) birinchi 3 soniyada ota-onaning tanish xavotiri (bola telefondan chiqmaydi, polda "
        "yotibdi, zerikkan, ta'til uzun); 2) burilish — bola noutbukni ochib, o'zi yasagan narsani "
        "ko'rsatadi (sayt, bot, o'yin, dizayn); 3) g'urur — ota yoki ona «barakalla»; 4) oxirgi "
        "kadr: «Sinov darsiga yozilish uchun izohlarda + qoldiring». Aktyorlar — haqiqiy "
        "o'quvchi va uning ota-onasi, gaplar sodda, hayotiy, o'zbekcha so'zlashuv."
    ),
    Post.Formula.RESULT: (
        "Haqiqiy natija: bitiruvchining onasi yoki otasi bilan qisqa suhbat (video ssenariysi). "
        "Suratga oluvchi beradigan 4–5 savol, qaysi kadrlar olinadi (yuz yaqin plandan, bola "
        "ishlayotgan ekran, sertifikat), va oxirgi jumla «…ota-onangiz faxriga aylaning» "
        "ruhida. Javoblarni o'ylab topma — faqat savollar va kadrlar."
    ),
    Post.Formula.QUESTION: (
        "Ota-onaga to'g'ridan-to'g'ri savol: bitta kuchli savol yoki hisob-kitob (masalan, "
        "«Farzandingiz kuniga 5 soat telefonda — bu yiliga 76 kun»). Izohda bahs boshlansin."
    ),
    Post.Formula.INSIDE: (
        "Hech kim ko'rmagan joy: dasturchi ishining ichi — sayt qanday ishlaydi, bot qanday "
        "javob beradi, dasturchining bir kuni. Qiziqish uyg'otsin, oddiy tilda."
    ),
    Post.Formula.TIPS: (
        "Foydali maslahat: saqlab qo'yiladigan aniq ro'yxat (3–5 band) — bolalar yoki yoshlar "
        "uchun kompyuter, AI, o'qish odatlari. Har band amaliy va tekshirsa bo'ladigan."
    ),
    Post.Formula.HUMOR: (
        "IT hazili: o'quvchi yoki dasturchi hayotidan tanish holat, bitta qisqa kulgili kuzatuv. "
        "Hech kimni kamsitmasin."
    ),
    Post.Formula.STORY: (
        "Motivatsion hikoya: noldan boshlagan yosh odamning yo'li bosqichma-bosqich (avval qanday "
        "edi → nima o'zgardi → hozir). Faqat faktlar ro'yxatidagi haqiqiy natijalardan foydalan; "
        "fakt bo'lmasa, umumiy hikoya qil va uni «masalan» deb ko'rsat, raqam o'ylab topma."
    ),
}

RULES = """Sen Navoiydagi «Sifat» IT o'quv markazining SMM mutaxassisisan.
Auditoriya: Navoiy viloyatidagi ota-onalar (9–17 yoshli farzandlari bor) va 16–25 yoshli yoshlar.

Qoidalar:
- Til: o'zbek tili, lotin yozuvi (o‘, g‘ — to'g'ri belgilar bilan), sodda so'zlashuv ohangi.
- Maqsad — his-tuyg'u va motivatsiya: xavotir, g'urur, qiziqish, kulgu. Quruq e'lon emas.
- Birinchi jumla eng kuchli: savol, muammo yoki kutilmagan fakt.
- Faqat berilgan faktlardan foydalan: kurs nomlari, narxlar, natijalar, raqamlar o'ylab
  topilmaydi. Fakt yo'q bo'lsa — umumiy gapir, raqamsiz.
- Raqobatchilar nomi tilga olinmaydi. Siyosat, din, boshqa markazlarni yomonlash yo'q.
- Emoji kam (matnda 3 tadan ko'p emas), heshteg 3–5 ta, oxirida.
- Taklif yumshoq: «izohlarda + qoldiring» yoki «botga yozing»; «tezda yoziling!» kabi bosim yo'q.
"""


def ready() -> bool:
    return bool(settings.GEMINI_API_KEY)


def cost(response: types.GenerateContentResponse) -> Decimal:
    usage = response.usage_metadata
    if usage is None:
        return Decimal(0)
    tokens_in = Decimal(usage.prompt_token_count or 0)
    tokens_out = Decimal((usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0))
    price_in = Decimal(str(settings.SMM_GEMINI_PRICE_INPUT))
    price_out = Decimal(str(settings.SMM_GEMINI_PRICE_OUTPUT))
    return (tokens_in * price_in + tokens_out * price_out) / MILLION


def ask[Schema: BaseModel](
    system: str, prompt: str, schema: type[Schema]
) -> tuple[Schema, Decimal]:
    """Gemini'dan tuzilgan javob: (javob, xarajat $)."""
    if not ready():
        raise AiError("GEMINI_API_KEY sozlanmagan.")
    client = genai.Client(
        api_key=settings.GEMINI_API_KEY, http_options=types.HttpOptions(timeout=TIMEOUT_MS)
    )
    try:
        response = client.models.generate_content(
            model=settings.SMM_GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_schema=schema,
                max_output_tokens=12_000,
                temperature=1.0,
                thinking_config=types.ThinkingConfig(
                    thinking_level=types.ThinkingLevel(settings.SMM_GEMINI_THINKING.upper())
                ),
            ),
        )
    except genai_errors.APIError as exc:
        logger.warning("Gemini xatosi (SMM): %s", exc)
        raise AiError(f"AI javob bermadi: {exc}") from exc
    except Exception as exc:  # tarmoq: httpx timeout, ulanish uzildi va h.k.
        logger.warning("Gemini'ga ulanib bo'lmadi (SMM): %s", exc)
        raise AiError(f"AI bilan aloqa yo'q: {exc}") from exc
    parsed = response.parsed
    try:
        result = (
            parsed
            if isinstance(parsed, schema)
            else schema.model_validate_json(response.text or "")
        )
    except ValueError as exc:
        raise AiError("AI javobi o'qilmadi.") from exc
    return result, cost(response)


def facts() -> str:
    """Agent tayanadigan faktlar: e'lon qilingan kurslar va sozlamadagi ro'yxat."""
    lines = []
    courses = Course.objects.filter(status=Course.Status.PUBLISHED).order_by("order", "title")[:30]
    for course in courses:
        parts = [course.title]
        if course.age_min or course.age_max:
            parts.append(f"{course.age_min or ''}–{course.age_max or ''} yosh")
        if course.price_offline_monthly:
            parts.append(f"oyiga {course.price_offline_monthly:,} so'm".replace(",", " "))
        elif course.price_online:
            parts.append(f"{course.price_online:,} so'm".replace(",", " "))
        if course.is_free:
            parts.append("bepul")
        lines.append("- Kurs: " + ", ".join(parts))
    about = SmmSettings.load().about.strip()
    if about:
        lines += [f"- {line.strip()}" for line in about.splitlines() if line.strip()]
    return "\n".join(lines) or "- (faktlar kiritilmagan)"


# --- Haftalik reja ---


class PlanItem(BaseModel):
    index: int
    topic: str
    angle: str


class Plan(BaseModel):
    items: list[PlanItem]


def plan(slots: list[Post], recent: list[str]) -> Decimal:
    """Bo'sh mavzuli postlarga mavzu va g'oya yozadi (joyida). Qaytadi: xarajat."""
    lines = [
        f"{index}. {WEEKDAYS[localtime(post.publish_at).weekday()]} "
        f"{localtime(post.publish_at):%d.%m}, {post.get_kind_display()}: "
        f"{FORMULAS[Post.Formula(post.formula)]}"
        for index, post in enumerate(slots)
    ]
    prompt = (
        "Keyingi hafta uchun har bir o'ringa mavzu (qisqa, 1 jumla) va g'oya (2–3 jumla: "
        "hikoya, his, birinchi kadr yoki birinchi jumla) yoz. Mavzular bir-biridan farq qilsin.\n\n"
        "O'rinlar:\n" + "\n".join(lines) + "\n\nFaktlar:\n" + facts()
    )
    if recent:
        prompt += "\n\nOldingi mavzular (takrorlama):\n" + "\n".join(f"- {t}" for t in recent)
    result, spent = ask(RULES, prompt, Plan)
    by_index = {item.index: item for item in result.items}
    for index, post in enumerate(slots):
        item = by_index.get(index)
        if item is None:
            raise AiError(f"Rejada {index}-o'rin yo'q.")
        post.topic = item.topic.strip()[:300]
        post.angle = item.angle.strip()
    return spent


# --- Post mazmuni ---


class Slide(BaseModel):
    title: str
    body: str


class Scene(BaseModel):
    seconds: str
    shot: str
    action: str
    line: str


class Draft(BaseModel):
    lead: str
    key: str
    tail: str
    glyph: str
    slides: list[Slide]
    roles: list[str]
    props: list[str]
    scenes: list[Scene]
    caption_ig: str
    caption_tg: str


SHAPES = {
    Post.Kind.POST: (
        "Bitta rasm (1080×1350). lead — oq kirish qatori (3–6 so'z), key — eng kuchli so'z yoki "
        "raqam (1–3 so'z, KATTA HARFDA), tail — kulrang davomi (3–8 so'z), glyph — fondagi katta "
        "belgi (1–4 belgi: raqam, ?, %, $, </>). slides, roles, props, scenes — bo'sh."
    ),
    Post.Kind.CAROUSEL: (
        "Karusel: lead/key/tail/glyph — birinchi (muqova) slayd uchun, keyin slides — 3–6 ta "
        "slayd (title: 2–6 so'z, body: 1–3 qisqa jumla, jami 220 belgidan oshmasin). Oxirgi "
        "slayd — yumshoq taklif. roles, props, scenes — bo'sh."
    ),
    Post.Kind.SCRIPT: (
        "Suratga olish ssenariysi (telefon, 9:16). lead/key/tail/glyph — videoning muqovasi "
        "uchun. roles — rollar (masalan «Ona», «O'g'il, 12 yosh»), props — kerakli narsalar, "
        "scenes — 6–10 ta kadr: seconds («0–3»), shot (plan: yaqin, umumiy, ekran), action "
        "(nima bo'ladi), line (aytiladigan gap, bo'lmasa bo'sh). slides — bo'sh. caption_ig va "
        "caption_tg — video chiqqanda qo'yiladigan matn."
    ),
}


def write(post: Post) -> tuple[Draft, Decimal]:
    formula = FORMULAS[Post.Formula(post.formula)]
    prompt = (
        f"Format: {SHAPES[Post.Kind(post.kind)]}\n\nFormula: {formula}\n\n"
        f"Mavzu: {post.topic}\nG'oya: {post.angle}\n\n"
        "caption_ig — Instagram izohi (400–900 belgi: birinchi qator — ilmoq, keyin hikoya, "
        "oxirida taklif va heshteglar). caption_tg — Telegram kanal uchun qisqaroq (300–700 "
        "belgi), heshtegsiz.\n\nFaktlar:\n" + facts()
    )
    return ask(RULES, prompt, Draft)
