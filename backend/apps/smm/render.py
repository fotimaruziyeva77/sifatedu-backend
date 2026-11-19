"""Post rasmlari sifatedu.uz sayti uslubida (brand/tools/muqovalar.py bilan bir xil): to'q fon,
nuqtali to'r, binafsha va qizil yorug'lik, oq sarlavha va qizil urg'u so'z ostida to'lqin chiziq.
Odam va ikonka yo'q — faqat tipografiya. O'lcham 1080×1350 (Instagram 4:5)."""

import io
import math
from functools import cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1350
BG = (11, 13, 26)
FG = (238, 240, 250)
MUTED = (155, 161, 196)
RED = (255, 59, 69)
LINE = (143, 152, 255)
CARD = (19, 22, 41)
ASSETS = Path(__file__).parent / "fonts"
FONT = ASSETS / "geologica-latin.ttf"
MONO = ASSETS / "martian-mono-latin.ttf"
LOGO = ASSETS / "logo.png"
HANDLE = "sifatedu.uz  ·  Navoiy"
LEFT = 80
WIDTH = W - 2 * LEFT


@cache
def font(size: int, weight: int, mono: bool = False) -> ImageFont.FreeTypeFont:
    face = ImageFont.truetype(str(MONO if mono else FONT), size)
    face.set_variation_by_axes([weight] if mono else [weight, 0])
    return face


# AI ba'zan o'zbek harfini boshqa belgi bilan yozadi (oʻ, o`), emoji yoki strelka qo'yadi.
# Shriftda yo'q belgi rasmda bo'sh to'rtburchak bo'lib chiqadi — almashtiriladi yoki olinadi.
SUBSTITUTE = str.maketrans({"ʻ": "‘", "ʼ": "’", "`": "’", "→": "-"})
MISSING = ""  # shaxsiy hudud: shriftda yo'qligi aniq (.notdef namunasi)


@cache
def supported(char: str) -> bool:
    if char.isspace():
        return True
    face = font(64, 700)
    return bytes(face.getmask(char)) != bytes(face.getmask(MISSING))


def clean(text: str) -> str:
    text = text.translate(SUBSTITUTE)
    return " ".join("".join(char for char in text if supported(char)).split())


def wrap(
    draw: ImageDraw.ImageDraw, text: str, face: ImageFont.FreeTypeFont, width: int
) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        line = ""
        for word in paragraph.split():
            trial = f"{line} {word}".strip()
            if draw.textlength(trial, font=face) <= width or not line:
                line = trial
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return [line for line in lines if line] or [""]


def glow(
    canvas: Image.Image,
    center: tuple[int, int],
    radius: int,
    colour: tuple[int, int, int],
    strength: float,
) -> None:
    """Yumshoq dumaloq yorug'lik. `radial_gradient` — markazdan masofa (chetda 128), shuning
    uchun chetda nolga tushadi; kanvasdan chiqqan qismi `paste` bilan kesiladi."""
    size = radius * 2
    mask = Image.radial_gradient("L").resize((size, size), Image.Resampling.BILINEAR)
    mask = mask.point(lambda value: int(max(0.0, 1 - value / 128) ** 1.6 * 255 * strength))
    spot = Image.new("RGBA", (size, size), (*colour, 0))
    spot.putalpha(mask)
    layer = Image.new("RGBA", canvas.size, (*colour, 0))
    layer.paste(spot, (center[0] - radius, center[1] - radius))
    canvas.alpha_composite(layer)


def background() -> Image.Image:
    canvas = Image.new("RGBA", (W, H), (*BG, 255))
    glow(canvas, (800, 420), 620, (70, 72, 150), 0.55)
    glow(canvas, (160, 1150), 560, (140, 24, 44), 0.45)
    dots = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dots)
    for y in range(18, H, 36):
        for x in range(18, W, 36):
            draw.ellipse((x - 1.6, y - 1.6, x + 1.6, y + 1.6), fill=(*LINE, 34))
    canvas.alpha_composite(dots)
    return canvas


def giant(canvas: Image.Image, glyph: str, top: int) -> None:
    """Fonda ulkan konturli belgi (o'ngga surilgan, cheti kesilishi mumkin)."""
    glyph = glyph.strip()[:4]
    if not glyph:
        return
    size = 560 if len(glyph) <= 2 else 400 if len(glyph) == 3 else 300
    face = font(size, 900)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    box = draw.textbbox((0, 0), glyph, font=face, stroke_width=4)
    width = box[2] - box[0]
    x = W - width + 60 - box[0] if width < 760 else (W - width) // 2 - box[0]
    draw.text(
        (x, top - box[1]),
        glyph,
        font=face,
        fill=(0, 0, 0, 0),
        stroke_width=4,
        stroke_fill=(*LINE, 90),
    )
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(0.6)))


def header(canvas: Image.Image, tag: str) -> None:
    logo = Image.open(LOGO).convert("RGBA")
    logo = logo.crop(logo.getbbox())
    logo = logo.resize((210, round(210 * logo.height / logo.width)), Image.Resampling.LANCZOS)
    canvas.alpha_composite(logo, (LEFT, 92))
    if not tag:
        return
    draw = ImageDraw.Draw(canvas)
    chip = font(26, 500, mono=True)
    width = draw.textlength(tag, font=chip)
    x1, y0 = W - LEFT, 80
    x0 = x1 - width - 92
    draw.rounded_rectangle(
        (x0, y0, x1, y0 + 60), radius=30, fill=(*CARD, 235), outline=(*LINE, 70), width=2
    )
    draw.ellipse((x0 + 24, y0 + 22, x0 + 40, y0 + 38), fill=RED)
    draw.text((x0 + 56, y0 + 30), tag, font=chip, fill=MUTED, anchor="lm")


def footer(canvas: Image.Image, page: str = "") -> None:
    draw = ImageDraw.Draw(canvas)
    small = font(26, 500, mono=True)
    y = H - 84
    draw.ellipse((LEFT, y - 6, LEFT + 12, y + 6), fill=RED)
    draw.text((LEFT + 26, y), HANDLE, font=small, fill=MUTED, anchor="lm")
    if page:
        draw.text((W - LEFT, y), page, font=small, fill=MUTED, anchor="rm")


def squiggle(draw: ImageDraw.ImageDraw, x0: float, x1: float, y: float) -> None:
    points, x = [], x0
    while x <= x1:
        points.append((x, y + 8 * math.sin((x - x0) / 20)))
        x += 3
    draw.line(points, fill=RED, width=7, joint="curve")


def fitted(
    draw: ImageDraw.ImageDraw, text: str, start: int, weight: int, lines: int
) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    size = start
    while True:
        face = font(size, weight)
        rows = wrap(draw, text, face, WIDTH)
        if size <= 40 or (
            len(rows) <= lines and max(draw.textlength(r, font=face) for r in rows) <= WIDTH
        ):
            return face, rows
        size -= 6


def cover(lead: str, key: str, tail: str, glyph: str, tag: str, page: str = "") -> Image.Image:
    """Muqova: oq kirish, qizil urg'u (to'lqin chiziq bilan), kulrang davomi."""
    lead, key, tail, glyph = clean(lead), clean(key), clean(tail), clean(glyph)
    canvas = background()
    giant(canvas, glyph, 230)
    header(canvas, tag)
    draw = ImageDraw.Draw(canvas)
    lead_font, lead_rows = fitted(draw, lead, 80, 820, 3)
    key_font, key_rows = fitted(draw, key.upper(), 132, 900, 2)
    tail_font = font(46, 500)
    tail_rows = wrap(draw, tail, tail_font, WIDTH)[:3]
    lead_step, key_step, tail_step = round(lead_font.size * 1.16), round(key_font.size * 1.08), 60
    block = len(lead_rows) * lead_step + len(key_rows) * key_step + 52 + len(tail_rows) * tail_step
    y = H - 170 - block
    for row in lead_rows:
        draw.text((LEFT, y), row, font=lead_font, fill=FG, anchor="lt")
        y += lead_step
    for index, row in enumerate(key_rows):
        draw.text((LEFT, y), row, font=key_font, fill=RED, anchor="lt")
        if index == len(key_rows) - 1:
            squiggle(
                draw,
                LEFT + 4,
                LEFT + draw.textlength(row, font=key_font) - 4,
                y + key_font.size * 0.98,
            )
        y += key_step
    y += 52
    for row in tail_rows:
        draw.text((LEFT, y), row, font=tail_font, fill=MUTED, anchor="lt")
        y += tail_step
    footer(canvas, page)
    return canvas.convert("RGB")


def slide(title: str, body: str, number: int, page: str) -> Image.Image:
    """Karusel ichki slaydi: katta raqam, sarlavha, matn kartochkada."""
    title, body = clean(title), clean(body)
    canvas = background()
    header(canvas, "")
    draw = ImageDraw.Draw(canvas)
    numeral = font(150, 900)
    draw.text((LEFT, 250), f"{number:02d}", font=numeral, fill=RED, anchor="lt")
    title_font, title_rows = fitted(draw, title, 88, 840, 3)
    y = 470
    for row in title_rows:
        draw.text((LEFT, y), row, font=title_font, fill=FG, anchor="lt")
        y += round(title_font.size * 1.15)
    y += 40
    body_font = font(46, 480)
    body_rows = wrap(draw, body, body_font, WIDTH - 80)[:8]
    card_bottom = y + 60 + len(body_rows) * 64
    draw.rounded_rectangle(
        (LEFT - 10, y, W - LEFT + 10, card_bottom),
        radius=28,
        fill=(*CARD, 230),
        outline=(*LINE, 60),
        width=2,
    )
    draw.rectangle((LEFT - 10, y + 28, LEFT - 2, card_bottom - 28), fill=RED)
    y += 30
    for row in body_rows:
        draw.text((LEFT + 34, y), row, font=body_font, fill=MUTED, anchor="lt")
        y += 64
    footer(canvas, page)
    return canvas.convert("RGB")


def jpeg(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=92, optimize=True)
    return buffer.getvalue()
