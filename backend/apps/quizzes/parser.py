"""Savollarni oddiy matndan kiritish ("Tez kiritish").

    ? HTML nimaning qisqartmasi?
    + HyperText Markup Language
    - High Tech Modern Language
    > Izoh: HTML — sahifa tuzilmasi uchun belgilash tili.

    ? Brauzer qaysi dasturlash tilini tushunadi?
    = JavaScript
    = JS

    ? Sahifa qanday yuklanadi? Tartibga qo'ying.
    1. HTML o'qiladi
    2. CSS qo'llanadi
    3. JavaScript ishga tushadi

    ? Moslang:
    HTML :: tuzilma
    CSS :: ko'rinish

Qoidalar: `?` — yangi savol; `+`/`-` — to'g'ri/noto'g'ri variant (bir nechta `+` — bir nechta
to'g'ri javob); `=` — matn javob; `1.` — tartib; `chap :: o'ng` — juft; `>` — izoh; savoldan
keyingi ``` ichidagi qatorlar — kod parchasi.
"""

import re
from dataclasses import dataclass, field

from .grading import DraftChoice, problems
from .models import Question

Kind = Question.Kind
NUMBERED = re.compile(r"^(\d+)[.)]\s+(.+)$")


@dataclass
class DraftQuestion:
    line: int
    text: str
    code: list[str] = field(default_factory=list)
    language: str = ""
    explanation: list[str] = field(default_factory=list)
    options: list[DraftChoice] = field(default_factory=list)
    answers: list[str] = field(default_factory=list)
    steps: list[tuple[int, str]] = field(default_factory=list)
    pairs: list[DraftChoice] = field(default_factory=list)

    @property
    def kind(self) -> str:
        if self.pairs:
            return Kind.MATCH
        if self.steps:
            return Kind.ORDER
        if self.answers:
            return Kind.TEXT
        correct = sum(1 for option in self.options if option.is_correct)
        return Kind.MULTIPLE if correct > 1 else Kind.SINGLE

    @property
    def choices(self) -> list[DraftChoice]:
        kind = self.kind
        if kind == Kind.MATCH:
            return self.pairs
        if kind == Kind.ORDER:
            return [DraftChoice(text) for _number, text in sorted(self.steps)]
        if kind == Kind.TEXT:
            return [DraftChoice(answer, is_correct=True) for answer in self.answers]
        return self.options


class ParseError(ValueError):
    """Qator raqamlari bilan: o'qituvchi aynan qayerni tuzatishni ko'radi."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("\n".join(errors))
        self.errors = errors


def parse(source: str) -> list[DraftQuestion]:
    questions: list[DraftQuestion] = []
    errors: list[str] = []
    current: DraftQuestion | None = None
    in_code = False

    for number, raw in enumerate(source.splitlines(), start=1):
        line = raw.rstrip()
        stripped = line.strip()
        if current is not None and stripped.startswith("```"):
            in_code = not in_code
            if in_code:
                current.language = stripped.removeprefix("```").strip()[:20]
            continue
        if in_code and current is not None:
            current.code.append(line)
            continue
        # Bo'sh qator, izoh va "---" kabi ajratgichlar tashlab ketiladi.
        if not stripped or stripped.startswith("#") or set(stripped) <= set("-=*_"):
            continue
        if stripped.startswith("?"):
            current = DraftQuestion(line=number, text=stripped[1:].strip())
            questions.append(current)
            if not current.text:
                errors.append(f"{number}-qator: savol matni bo'sh.")
            continue
        if current is None:
            errors.append(f"{number}-qator: avval «?» bilan savol yozing.")
            continue
        marker, rest = stripped[0], stripped[1:].strip()
        if marker in "+-" and rest:
            current.options.append(DraftChoice(rest, is_correct=marker == "+"))
        elif marker == "=" and rest:
            current.answers.append(rest)
        elif marker == ">" and rest:
            current.explanation.append(rest.removeprefix("Izoh:").strip())
        elif match := NUMBERED.match(stripped):
            current.steps.append((int(match.group(1)), match.group(2).strip()))
        elif "::" in stripped:
            left, right = (part.strip() for part in stripped.split("::", 1))
            if left and right:
                current.pairs.append(DraftChoice(left, match=right))
            else:
                errors.append(f"{number}-qator: juftning ikkala tomoni ham kerak (chap :: o'ng).")
        else:
            errors.append(f"{number}-qator: tushunarsiz qator — «{stripped[:40]}».")

    if in_code:
        errors.append("Kod bloki yopilmagan (``` yetishmayapti).")
    for question in questions:
        kinds = [bool(question.options), bool(question.answers), bool(question.steps)]
        kinds.append(bool(question.pairs))
        if sum(kinds) > 1:
            errors.append(
                f"{question.line}-qator: bitta savolda turli xil javoblar aralashgan "
                "(+/-, =, 1., :: dan faqat bittasi)."
            )
            continue
        errors.extend(
            f"{question.line}-qator: {problem}"
            for problem in problems(question.kind, question.choices)
        )
    if not questions and not errors:
        errors.append("Birorta ham savol topilmadi.")
    if errors:
        raise ParseError(errors)
    return questions
