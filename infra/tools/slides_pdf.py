"""Dars slaydlarini PDF qilish (dasturchi kompyuterida): backend/content/.../<dars>.pdf.

    python infra/tools/slides_pdf.py python

1. backend konteyneri: `import_course <kurs> --json` — slaydlar (saytdagi tuzilma) va matn xeshi;
2. frontend konteyneri: saytdagi `Slide` komponenti bilan statik HTML (frontend/scripts/slides-pdf);
3. Google Chrome (headless): HTML → PDF, har slayd 1280×720 varaq;
4. modul papkasidagi `_pdf.toml` ga slayd matnining xeshi yoziladi — matn o'zgarsa, `import_course`
   PDF eskirganini aytadi va uni yuklamaydi.

Kerak: `docker compose` (backend ishlab turgan, frontend konteyneri yig'ilgan) va Google Chrome
(boshqa joyda bo'lsa — CHROME muhit o'zgaruvchisi). PDF'lar repoga commit qilinadi; serverda
`import_course` ularni darsga «Slaydlar (PDF)» materiali qilib yuklaydi. Slayd dizayni
(`slides.css`) o'zgarsa ham PDF'larni qayta yasang.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "backend" / "content"
OUT = ROOT / "frontend" / "scripts" / "slides-pdf" / ".out"
CHROMES = [
    os.environ.get("CHROME", ""),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
]
MANIFEST_HEAD = (
    "# PDF qaysi slayd matnidan yasalgan (sha256). Qo'lda o'zgartirmang —\n"
    "# python infra/tools/slides_pdf.py yozadi.\n"
)


def run(command: list[str], **options: object) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(command, cwd=ROOT, check=True, **options)  # type: ignore[call-overload]


def chrome() -> str:
    for candidate in CHROMES:
        if candidate and Path(candidate).is_file():
            return candidate
    sys.exit("Google Chrome topilmadi: CHROME=<chrome yo'li> bilan ishga tushiring.")


def main(course: str) -> None:
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    exported = run(
        ["docker", "compose", "exec", "-T", "backend"]
        + ["python", "manage.py", "import_course", course, "--json"],
        capture_output=True,
    ).stdout
    (OUT / "input.json").write_bytes(exported)
    lessons = json.loads(exported)["lessons"]
    print(f"{course}: {len(lessons)} dars — HTML yasalmoqda…")
    run(
        ["docker", "compose", "run", "--rm", "--no-deps", "-T", "frontend", "sh", "-c"]
        + ["cd /app && npx vitest run --config scripts/slides-pdf/vitest.config.mts"],
        capture_output=True,
    )
    browser = chrome()
    manifests: dict[Path, dict[str, str]] = {}
    with tempfile.TemporaryDirectory() as profile:
        for lesson in lessons:
            html = OUT / f"{lesson['path'].replace('/', '__')}.html"
            pdf = CONTENT / f"{lesson['path']}.pdf"
            run(
                [
                    browser,
                    "--headless=new",
                    "--disable-gpu",
                    "--no-first-run",
                    "--no-pdf-header-footer",
                    f"--user-data-dir={profile}",
                    "--virtual-time-budget=20000",
                    f"--print-to-pdf={pdf}",
                    html.as_uri(),
                ],
                capture_output=True,
            )
            manifests.setdefault(pdf.parent, {})[pdf.stem] = lesson["hash"]
            print(f"  {pdf.relative_to(ROOT)} — {pdf.stat().st_size // 1024} KB")
    for folder, hashes in manifests.items():
        lines = [f'"{stem}" = "{digest}"' for stem, digest in sorted(hashes.items())]
        (folder / "_pdf.toml").write_text(
            MANIFEST_HEAD + "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
        )
    shutil.rmtree(OUT, ignore_errors=True)
    print("Tayyor. PDF'lar va _pdf.toml ni commit qiling.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Ishlatish: python infra/tools/slides_pdf.py <kurs>  (masalan: python)")
    main(sys.argv[1])
