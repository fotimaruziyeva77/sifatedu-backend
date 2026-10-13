"""`.po` → `.mo` Python'ning o'zida: serverdagi Docker image'da gettext (`msgfmt`) yo'q.

Faqat loyihaning o'z tarjimalari uchun (`LOCALE_PATHS`): oddiy va ko'plik yozuvlar, ko'p qatorli
matnlar, `#, fuzzy` (tashlab ketiladi). Kontekst (`msgctxt`) ishlatilmaydi.
"""

import array
import ast
import struct
from pathlib import Path

from django.conf import settings

MAGIC = 0x950412DE


def parse(text: str) -> dict[str, str]:
    """Yozuvlar: kalit — msgid (ko'plikda `msgid\\0msgid_plural`), qiymat — tarjima (ko'plikda
    shakllar `\\0` bilan). Tarjimasiz va `fuzzy` yozuvlar kirmaydi; sarlavha (`""`) kiradi."""
    messages: dict[str, str] = {}
    entry: dict[str, str] = {}
    fuzzy = False
    field = ""

    def flush() -> None:
        nonlocal entry, fuzzy
        if "msgid" in entry and not fuzzy:
            key = entry["msgid"]
            if "msgid_plural" in entry:
                key += "\0" + entry["msgid_plural"]
                forms = sorted(name for name in entry if name.startswith("msgstr["))
                value = "\0".join(entry[name] for name in forms)
            else:
                value = entry.get("msgstr", "")
            if value.replace("\0", ""):
                messages[key] = value
        entry, fuzzy = {}, False

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            if line.startswith("#,") and "fuzzy" in line:
                flush()
                fuzzy = True
            continue
        if line.startswith('"'):
            entry[field] += ast.literal_eval(line)
            continue
        name, _, rest = line.partition(" ")
        if name == "msgid" and "msgid" in entry:
            flush()
        field = name
        entry[field] = ast.literal_eval(rest.strip())
    flush()
    return messages


def compile_messages(messages: dict[str, str]) -> bytes:
    """GNU `.mo` formati (CPython'ning Tools/i18n/msgfmt.py kabi)."""
    keys = sorted(messages)
    ids = strs = b""
    table = []
    for key in keys:
        encoded_key, encoded_value = key.encode(), messages[key].encode()
        table.append((len(ids), len(encoded_key), len(strs), len(encoded_value)))
        ids += encoded_key + b"\0"
        strs += encoded_value + b"\0"
    key_start = 7 * 4 + 16 * len(keys)
    value_start = key_start + len(ids)
    key_offsets: list[int] = []
    value_offsets: list[int] = []
    for key_offset, key_length, value_offset, value_length in table:
        key_offsets += [key_length, key_offset + key_start]
        value_offsets += [value_length, value_offset + value_start]
    header = struct.pack("Iiiiiii", MAGIC, 0, len(keys), 7 * 4, 7 * 4 + len(keys) * 8, 0, 0)
    return header + array.array("i", key_offsets + value_offsets).tobytes() + ids + strs


def po_files() -> list[Path]:
    return sorted(
        path for root in settings.LOCALE_PATHS for path in Path(root).glob("*/LC_MESSAGES/*.po")
    )


def compiled(po_path: Path) -> bytes:
    return compile_messages(parse(po_path.read_text(encoding="utf-8")))
