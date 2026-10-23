"""Dars slaydlari: Markdown → saytda ko'rsatiladigan slaydlar (JSON).

Slaydlar alohida `---` qatori bilan ajraladi (kod bloki ichidagisi hisobga olinmaydi). HTML yozib
bo'lmaydi (`html=False` — matn bo'lib chiqadi), havolalar faqat http(s), mailto va sayt ichidagi
yo'llar.

Bitta slayd (brend uslubidagi dars taqdimoti):

    ###### 02 · List               — ustki kichik yozuv
    ## List: tartibli ro'yxat       — sarlavha (`#` — muqova yoki bo'lim slaydi)
    matn, ro'yxat, kod, jadval, `>` eslatma
    |||                             — ustunlarga ajratish
    ### Karta sarlavhasi {.sariq}   — karta (`####` — kichik yorliq); ketma-ket kartalar — to'r.
                                      Rang: {.qizil} {.sariq} {.yashil} {.kok}; «01 Nomi» — raqamli
    ***                             — kartalar to'rini yopish (keyingisi to'liq kenglikda)

Slayd turi: birinchi slayd `#` bilan — muqova, keyingi `#` — bo'lim (qizil fon). Ustki yozuv
«Amaliyot…» — amaliyot slaydi (raqamli ro'yxat — topshiriq kartalari, `>` — qizil banner),
«Xulosa…» — yakuniy, «Viktorina…» — savollar. Kod bloki tili `indeks` (`mevalar = ["olma", "anor"]`)
— indekslar sxemasi; `text` — ekranda chiqadigan natija.

Ichki matn tugunlari: ["t", matn] · ["b", [...]] qalin · ["i", [...]] kursiv · ["s", [...]]
o'chirilgan · ["c", matn] kod · ["a", havola, [...]] · ["br"] yangi qator.
"""

import ast
import re
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token
from pygments import lex
from pygments.lexer import Lexer
from pygments.lexers import get_lexer_by_name
from pygments.token import Token as T
from pygments.token import _TokenType
from pygments.util import ClassNotFound

MD = MarkdownIt("commonmark", {"html": False}).enable(["table", "strikethrough"])
MAX_SLIDES = 80
SAFE_LINK = ("http://", "https://", "mailto:", "/", "#")
COLUMN = "|||"
INDEX_LANGUAGE = "indeks"
MAX_INDEX_ITEMS = 12
MAX_INDEX_SOURCE = 400
TONES = ("qizil", "sariq", "yashil", "kok")
TONE = re.compile(r"\s*\{\.([a-z]+)\}\s*$")
NUMBER = re.compile(r"^(\d{2})\s+")
# Ustki yozuvning birinchi so'zi (bo'lim raqamidan keyin: «04 · Viktorina») → slayd turi.
KINDS = (("amaliyot", "practice"), ("xulosa", "summary"), ("viktorina", "quiz"))
SECTION_NUMBER = re.compile(r"^\d+\s*[·.:-]?\s*")
LANGUAGES = {
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "sh": "bash",
    "shell": "bash",
    "console": "bash",
    "vue": "html",
    "": "text",
}
# Kod ranglari: Pygments token turi → qisqa sinf (saytdagi CSS shu nomlar bilan).
CLASSES: list[tuple[_TokenType, str]] = [
    (T.Comment, "c"),
    (T.Keyword.Constant, "kc"),
    (T.Keyword, "k"),
    (T.Name.Builtin, "nb"),
    (T.Name.Function, "nf"),
    (T.Name.Class, "nc"),
    (T.Name.Decorator, "nd"),
    (T.Name.Tag, "nt"),
    (T.Name.Attribute, "na"),
    (T.Literal.String, "s"),
    (T.Literal.Number, "m"),
    (T.Operator.Word, "k"),
    (T.Operator, "o"),
    (T.Punctuation, "p"),
    (T.Generic.Prompt, "gp"),
    (T.Generic.Output, "go"),
    # ```diff```: «-» qatorlar — xato (qizil), «+» — to'g'ri (yashil)
    (T.Generic.Deleted, "gd"),
    (T.Generic.Inserted, "gi"),
]


def chunks(text: str, separator: str) -> list[str]:
    """`separator` qatori bo'yicha bo'laklar (kod bloki ichidagi qatorlar hisobga olinmaydi)."""
    parts: list[list[str]] = [[]]
    fence = ""
    for line in text.replace("\r\n", "\n").split("\n"):
        stripped = line.strip()
        if fence:
            if stripped.startswith(fence):
                fence = ""
        elif stripped.startswith(("```", "~~~")):
            fence = stripped[:3]
        elif stripped == separator:
            parts.append([])
            continue
        parts[-1].append(line)
    return ["\n".join(part).strip() for part in parts]


def split(markdown: str) -> list[str]:
    """Slaydlarga ajratadi: alohida `---` qatori (kod bloki ichida emas)."""
    return [slide for slide in chunks(markdown, "---") if slide]


def css_class(kind: _TokenType) -> str:
    for base, name in CLASSES:
        if kind in base:
            return name
    return ""


def lexer_for(language: str) -> Lexer:
    name = LANGUAGES.get(language.lower(), language.lower())
    try:
        return get_lexer_by_name(name, stripnl=False, ensurenl=False)
    except ClassNotFound:
        return get_lexer_by_name("text", stripnl=False, ensurenl=False)


def highlight(code: str, language: str) -> list[list[list[str]]]:
    """Kod qatorlari: har qator — [[sinf, matn], ...]. Bir xil sinfli bo'laklar birlashtiriladi."""
    lines: list[list[list[str]]] = [[]]
    # Oxirgi qator ham `\n` bilan: ba'zi lekserlar (diff) qatorni shu bilan taniydi.
    for kind, value in lex(code + "\n", lexer_for(language)):
        name = css_class(kind)
        for k, part in enumerate(value.split("\n")):
            if k:
                lines.append([])
            if not part:
                continue
            row = lines[-1]
            if row and row[-1][0] == name:
                row[-1][1] += part
            else:
                row.append([name, part])
    while len(lines) > 1 and not lines[-1]:
        lines.pop()
    return lines


def index_block(code: str) -> dict[str, Any] | None:
    """`mevalar = ["olma", "anor"]` yoki `soz = "Python"` → indekslar sxemasi (bo'lmasa None)."""
    name, separator, literal = code.strip().partition("=")
    if not separator or not name.strip().isidentifier() or len(literal) > MAX_INDEX_SOURCE:
        return None
    try:
        value = ast.literal_eval(literal.strip())
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        return None
    if isinstance(value, str):
        items = list(value)
    elif isinstance(value, list | tuple):
        items = [f'"{item}"' if isinstance(item, str) else repr(item) for item in value]
    else:
        return None
    if not 0 < len(items) <= MAX_INDEX_ITEMS:
        return None
    return {"t": "index", "name": name.strip(), "items": items, "chars": isinstance(value, str)}


def safe_href(href: str) -> str:
    return href if href.startswith(SAFE_LINK) else ""


def inline(children: list[Token] | None) -> list[Any]:
    root: list[Any] = []
    stack = [root]

    def text(value: str) -> None:
        target = stack[-1]
        if target and target[-1][0] == "t":
            target[-1][1] += value
        else:
            target.append(["t", value])

    for token in children or []:
        kind = token.type
        if kind == "text":
            if token.content:
                text(token.content)
        elif kind == "code_inline":
            stack[-1].append(["c", token.content])
        elif kind in ("softbreak", "hardbreak"):
            stack[-1].append(["br"])
        elif kind in ("strong_open", "em_open", "s_open"):
            node: list[Any] = [{"strong_open": "b", "em_open": "i", "s_open": "s"}[kind], []]
            stack[-1].append(node)
            stack.append(node[1])
        elif kind == "link_open":
            link: list[Any] = ["a", safe_href(str(token.attrGet("href") or "")), []]
            stack[-1].append(link)
            stack.append(link[2])
        elif kind in ("strong_close", "em_close", "s_close", "link_close"):
            if len(stack) > 1:
                stack.pop()
        elif kind == "image":
            text(f"[{token.content}]")
        elif token.content:
            text(token.content)
    return root


def plain(nodes: list[Any]) -> str:
    """Ichki tugunlardagi oddiy matn."""
    parts = []
    for node in nodes:
        if node[0] in ("t", "c"):
            parts.append(node[1])
        elif node[0] in ("b", "i", "s"):
            parts.append(plain(node[1]))
        elif node[0] == "a":
            parts.append(plain(node[2]))
    return "".join(parts)


def closing(tokens: list[Token], start: int) -> int:
    """`*_open` tokeniga mos `*_close` indeksi."""
    opening = tokens[start].type
    closing_type = opening.replace("_open", "_close")
    depth = 0
    for index in range(start, len(tokens)):
        if tokens[index].type == opening:
            depth += 1
        elif tokens[index].type == closing_type:
            depth -= 1
            if depth == 0:
                return index
    return len(tokens) - 1


def list_block(tokens: list[Token]) -> dict[str, Any]:
    head = tokens[0]
    items: list[dict[str, Any]] = []
    index = 1
    while index < len(tokens) - 1:
        if tokens[index].type != "list_item_open":
            index += 1
            continue
        end = closing(tokens, index)
        body = tokens[index + 1 : end]
        content: list[Any] = []
        sub = None
        k = 0
        while k < len(body):
            token = body[k]
            if token.type in ("bullet_list_open", "ordered_list_open"):
                close = closing(body, k)
                sub = list_block(body[k : close + 1])
                k = close + 1
                continue
            if token.type == "inline":
                if content:
                    content.append(["br"])
                content.extend(inline(token.children))
            k += 1
        items.append({"inl": content, "sub": sub})
        index = end + 1
    ordered = head.type == "ordered_list_open"
    block: dict[str, Any] = {"t": "ol" if ordered else "ul", "items": items}
    if ordered:
        block["start"] = int(head.attrGet("start") or 1)
    return block


def table_block(tokens: list[Token]) -> dict[str, Any]:
    head: list[Any] = []
    rows: list[list[Any]] = []
    align: list[str] = []
    row: list[Any] | None = None
    for token in tokens:
        if token.type == "tr_open":
            row = []
        elif token.type == "th_open":
            style = str(token.attrGet("style") or "")
            align.append(style.removeprefix("text-align:") if style else "")
        elif token.type == "inline" and row is not None:
            row.append(inline(token.children))
        elif token.type == "tr_close" and row is not None:
            if not head:
                head = row
            else:
                rows.append(row)
            row = None
    return {"t": "table", "head": head, "rows": rows, "align": align}


def blocks(tokens: list[Token]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        kind = token.type
        if kind == "heading_open":
            out.append(
                {"t": "h", "level": int(token.tag[1]), "inl": inline(tokens[index + 1].children)}
            )
            index += 3
        elif kind == "paragraph_open":
            out.append({"t": "p", "inl": inline(tokens[index + 1].children)})
            index += 3
        elif kind in ("bullet_list_open", "ordered_list_open"):
            end = closing(tokens, index)
            out.append(list_block(tokens[index : end + 1]))
            index = end + 1
        elif kind in ("fence", "code_block"):
            language = (token.info or "").strip().split(" ")[0]
            code = token.content.rstrip("\n")
            scheme = index_block(code) if language.lower() == INDEX_LANGUAGE else None
            if scheme is None:
                if language.lower() == INDEX_LANGUAGE:
                    language = "python"
                scheme = {"t": "code", "lang": language, "lines": highlight(code, language)}
            out.append(scheme)
            index += 1
        elif kind == "table_open":
            end = closing(tokens, index)
            out.append(table_block(tokens[index : end + 1]))
            index = end + 1
        elif kind == "blockquote_open":
            end = closing(tokens, index)
            out.append({"t": "quote", "blocks": blocks(tokens[index + 1 : end])})
            index = end + 1
        elif kind == "hr":
            out.append({"t": "hr"})
            index += 1
        else:
            index += 1
    return out


def take_tone(nodes: list[Any]) -> str:
    """Sarlavha oxiridagi `{.sariq}` belgisi: matndan olinadi, rang nomi qaytadi."""
    if not nodes or nodes[-1][0] != "t":
        return ""
    match = TONE.search(nodes[-1][1])
    if match is None or match.group(1) not in TONES:
        return ""
    nodes[-1][1] = nodes[-1][1][: match.start()]
    if not nodes[-1][1]:
        nodes.pop()
    return match.group(1)


def take_number(nodes: list[Any]) -> str:
    """«01 Dictionary» → «01» (katta raqam), sarlavhada «Dictionary» qoladi."""
    if not nodes or nodes[0][0] != "t":
        return ""
    match = NUMBER.match(nodes[0][1])
    if match is None:
        return ""
    nodes[0][1] = nodes[0][1][match.end() :]
    if not nodes[0][1]:
        nodes.pop(0)
    return match.group(1)


def group(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """`###`/`####` va undan keyingi bloklar — karta; ketma-ket kartalar — bitta to'r (`cards`)."""
    out: list[dict[str, Any]] = []
    cards: dict[str, Any] | None = None
    for item in items:
        if item["t"] == "hr":
            cards = None
        elif item["t"] == "h" and item["level"] in (3, 4):
            title = item["inl"]
            tone = take_tone(title)
            card = {
                "title": title,
                "label": item["level"] == 4,
                "tone": tone,
                "num": take_number(title),
                "blocks": [],
            }
            if cards is None:
                cards = {"t": "cards", "cards": []}
                out.append(cards)
            cards["cards"].append(card)
        elif cards is not None:
            cards["cards"][-1]["blocks"].append(item)
        else:
            out.append(item)
    return out


def kind_of(level: int, number: int, kicker: list[Any]) -> str:
    if level == 1:
        return "cover" if number == 0 else "section"
    word = SECTION_NUMBER.sub("", plain(kicker).strip().lower())
    for prefix, kind in KINDS:
        if word.startswith(prefix):
            return kind
    return "plain"


def slide(markdown: str, number: int) -> dict[str, Any]:
    columns = [blocks(MD.parse(part)) for part in chunks(markdown, COLUMN)]
    head = columns[0]
    kicker: list[Any] = []
    title: list[Any] = []
    level = 0
    if head and head[0]["t"] == "h" and head[0]["level"] == 6:
        kicker = head.pop(0)["inl"]
    if head and head[0]["t"] == "h" and head[0]["level"] in (1, 2):
        top = head.pop(0)
        title, level = top["inl"], top["level"]
    filled = [column for column in columns if column]
    if len(filled) > 1:
        body = [{"t": "cols", "cols": [group(column) for column in filled]}]
    else:
        body = group(filled[0] if filled else [])
    kind = kind_of(level, number, kicker)
    return {"kind": kind, "kicker": kicker, "title": title, "blocks": body}


def render(markdown: str) -> list[dict[str, Any]]:
    """Slaydlar: [{"kind", "kicker", "title", "blocks"}, ...] (ko'pi bilan MAX_SLIDES)."""
    return [slide(chunk, number) for number, chunk in enumerate(split(markdown)[:MAX_SLIDES])]
