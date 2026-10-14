"""Qo'llanmadan test: fayl Gemini'ga beriladi, javob — tuzilgan JSON (structured output), u
«Tez kiritish» matniga aylantiriladi va `parser.py` bilan tekshiriladi. O'qituvchi matnni
tuzatib e'lon qiladi (`drafts.publish`).

PDF va rasmni Gemini o'zi o'qiydi; Word, PowerPoint va matn fayllaridan matnni o'zimiz olamiz
(qo'shimcha kutubxonasiz — ular ZIP ichidagi XML).
"""

import html
import io
import logging
import re
import zipfile
from typing import Literal

from django.conf import settings
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel

from .parser import ParseError, parse

logger = logging.getLogger(__name__)

QUESTIONS = 12
MAX_BYTES = 20 * 1024 * 1024
MAX_TEXT = 60_000  # belgi: juda uzun qo'llanma qisqartiriladi
MAX_UNZIPPED = 50 * 1024 * 1024
TIMEOUT_MS = 150_000
NATIVE = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}
OFFICE = {".docx", ".pptx"}
PLAIN = {".txt", ".md", ".py", ".html", ".css", ".js"}
# Word (w:) va PowerPoint (a:) xatboshilari va ulardagi matn bo'laklari.
PARAGRAPH = re.compile(r"<(?:w|a):p[ >].*?</(?:w|a):p>", re.S)
RUN = re.compile(r"<(?:w|a):t(?: [^>]*)?>(.*?)</(?:w|a):t>", re.S)
ALLOWED = set(NATIVE) | OFFICE | PLAIN

SYSTEM = """Sen tajribali o'qituvchisan. Dars qo'llanmasi asosida o'quvchilar uchun test tuzasan.

Qoidalar:
- Til: o'zbek tili, lotin yozuvi (o‘, g‘). Kod, buyruq va atamalar o'z holicha qoladi.
- Faqat qo'llanmadagi mavzu bo'yicha so'ra, qo'llanmada yo'q narsani so'rama.
- {count} ta savol: taxminan 8 tasi "single" (4 ta variant, bittasi to'g'ri), 2 tasi "multiple"
  (4–5 ta variant, 2–3 tasi to'g'ri), 2 tasi "text" (javob — bitta so'z, son yoki kod natijasi;
  "answers"ga 1–3 ta to'g'ri yozilishini yoz).
- Mavzu dasturlash bo'lsa, savollarning yarmida qisqa kod parchasi bo'lsin ("code" — 1–6 qator,
  "language" — masalan python), savol esa «Kod nima chiqaradi?» kabi.
- Savol va variantlar qisqa, bir qatorli; noto'g'ri variantlar ishonarli bo'lsin. «Barchasi
  to'g'ri», «Hech biri» kabi variantlardan qoch.
- Har savolga "explanation": bitta qisqa jumla — nega shu javob to'g'ri.
- Qiyinlik: boshlovchilar uchun — oson va o'rtacha.
- "topic": darsning qisqa nomi (5 so'zgacha).
- Ishlatilmaydigan maydonlar bo'sh: "code": "", "language": "", "options": [], "answers": [].
"""


class AiError(Exception):
    """O'qituvchiga ko'rsatiladigan sabab."""


class GenOption(BaseModel):
    text: str
    correct: bool


class GenQuestion(BaseModel):
    kind: Literal["single", "multiple", "text"]
    text: str
    code: str
    language: str
    options: list[GenOption]
    answers: list[str]
    explanation: str


class GenQuiz(BaseModel):
    topic: str
    questions: list[GenQuestion]


def ready() -> bool:
    """AI kaliti bormi (kalitsiz test tuzilmaydi)."""
    return bool(settings.GEMINI_API_KEY)


def suffix(name: str) -> str:
    match = re.search(r"\.[A-Za-z0-9]+$", name)
    return match.group(0).lower() if match else ""


def office_text(name: str, data: bytes) -> str:
    """Word va PowerPoint: ZIP ichidagi XML'dan xatboshilar matni. XML parser ishlatilmaydi —
    faqat matn teglari qidiriladi, shuning uchun XML hujumlari (entity bomb) ta'sir qilmaydi."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise AiError("Fayl ochilmadi: Word yoki PowerPoint fayli buzilgan.") from exc
    with archive:
        names = set(archive.namelist())
        if suffix(name) == ".docx":
            parts = [part for part in ("word/document.xml",) if part in names]
        else:
            slides = [n for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
            parts = sorted(slides, key=lambda n: int(re.findall(r"\d+", n)[-1]))
        if sum(archive.getinfo(part).file_size for part in parts) > MAX_UNZIPPED:
            raise AiError("Fayl juda katta.")
        lines = []
        for part in parts:
            xml = archive.read(part).decode("utf-8", errors="replace")
            for para in PARAGRAPH.findall(xml):
                text = "".join(html.unescape(run) for run in RUN.findall(para)).strip()
                if text:
                    lines.append(text)
    return "\n".join(lines)


def material_parts(name: str, data: bytes) -> list[types.Part]:
    ext = suffix(name)
    if ext not in ALLOWED:
        raise AiError(
            "Bu turdagi fayldan test tuzib bo'lmaydi: PDF, Word, PowerPoint, rasm yoki matn."
        )
    if ext in NATIVE:
        return [types.Part.from_bytes(data=data, mime_type=NATIVE[ext])]
    text = office_text(name, data) if ext in OFFICE else data.decode("utf-8", errors="replace")
    text = text.strip()
    if not text:
        raise AiError("Fayldan matn topilmadi. Uni PDF yoki rasm qilib yuklang.")
    return [types.Part.from_text(text=text[:MAX_TEXT])]


def one_line(value: str) -> str:
    return " ".join(value.split())


def block(question: GenQuestion) -> str:
    lines = [f"? {one_line(question.text)}"]
    code = question.code.strip("\n")
    if code.strip():
        lines += [f"```{one_line(question.language)}", *code.splitlines(), "```"]
    if question.kind == "text":
        lines += [f"= {one_line(answer)}" for answer in question.answers if answer.strip()]
    else:
        lines += [
            f"{'+' if option.correct else '-'} {one_line(option.text)}"
            for option in question.options
            if option.text.strip()
        ]
    if question.explanation.strip():
        lines.append(f"> {one_line(question.explanation)}")
    return "\n".join(lines)


def to_text(quiz: GenQuiz) -> str:
    """«Tez kiritish» matni: faqat `parser.py` qabul qiladigan savollar qoladi."""
    good = []
    for question in quiz.questions:
        candidate = block(question)
        try:
            parse(candidate)
        except ParseError as exc:
            logger.info("AI savoli tashlab ketildi: %s", exc.errors)
            continue
        good.append(candidate)
    if not good:
        raise AiError("AI yaroqli savol tuza olmadi. Boshqa fayl bilan qayta urinib ko'ring.")
    return "\n\n".join(good)


def call_model(parts: list[types.Part]) -> GenQuiz:
    """Gemini: tuzilgan javob (JSON sxema bo'yicha)."""
    client = genai.Client(
        api_key=settings.GEMINI_API_KEY, http_options=types.HttpOptions(timeout=TIMEOUT_MS)
    )
    ask = types.Part.from_text(text=f"Shu qo'llanma asosida {QUESTIONS} ta savol tuz.")
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=types.Content(role="user", parts=[*parts, ask]),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM.format(count=QUESTIONS),
            response_mime_type="application/json",
            response_schema=GenQuiz,
            max_output_tokens=16_000,
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel("LOW")),
        ),
    )
    parsed = response.parsed
    if isinstance(parsed, GenQuiz):
        return parsed
    return GenQuiz.model_validate_json(response.text or "")


def generate(name: str, data: bytes) -> tuple[str, str]:
    """(mavzu nomi, «Tez kiritish» matni)."""
    if not ready():
        raise AiError("AI kaliti sozlanmagan: serverda GEMINI_API_KEY kiritilishi kerak.")
    if len(data) > MAX_BYTES:
        raise AiError("Fayl 20 MB dan katta.")
    parts = material_parts(name, data)
    try:
        quiz = call_model(parts)
    except genai_errors.APIError as exc:
        logger.warning("Gemini xatosi (test tuzish): %s", exc)
        raise AiError("AI hozir javob bermadi. Bir ozdan keyin qayta urinib ko'ring.") from exc
    except ValueError as exc:  # JSON sxemaga mos kelmadi
        logger.warning("Gemini javobi o'qilmadi: %s", exc)
        raise AiError("AI javobi tushunarsiz bo'ldi. Qayta urinib ko'ring.") from exc
    return one_line(quiz.topic)[:200], to_text(quiz)
