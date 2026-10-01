# Sifat Edu — backend

Django 5.2 LTS + Django REST Framework. Admin panel — Django Admin (Unfold temasi), fon vazifalari — Celery.

## Tuzilma

```
config/            # settings (base, dev, prod, test), urls, asgi, celery
apps/
  core/            # health, xato formati, admin yordamchilari, HTML tozalash, telefon formati
  users/           # User (telefon bilan), rollar, SMS kodlar, Google va Telegram akkauntlari
  catalog/         # kategoriya, ustoz, kurs, modul, dars (kurs dasturi)
  content/         # landing kontenti: sozlamalar (hero, manifest, promo video), xavotirlar, afzalliklar,
                   # qadamlar, FAQ, fikrlar, huquqiy sahifalar
  leads/           # "Bepul maslahat" arizalari
  notifications/   # Telegram
scripts/entrypoint.sh
```

Har bir app ichida: `models.py`, `services.py` (biznes mantiq), `serializers.py`, `views.py`, `admin.py`, `tasks.py`, `tests/`.

## Katalog

Tuzilma: kategoriya → kurs → modul → dars. Kursdagi darslar soni va umumiy davomiylik
`Course.lesson_count` va `Course.total_duration_min` da saqlanadi va dastur o'zgarganda
signal orqali yangilanadi (`apps/catalog/signals.py`) — katalogda har kurs uchun qo'shimcha
so'rov bo'lmasligi uchun.

Qidiruv joriy til va o'zbekcha maydonlarda ishlaydi; tezlik uchun `pg_trgm` GIN indekslari
bor (`0003_course_search_indexes`). Video, materiallar va progress 4-qadamda qo'shiladi.

## API

- Prefiks: `/api/v1/`. Hujjat: `/api/docs/` (faqat `API_DOCS_ENABLED=true` bo'lsa).
- Autentifikatsiya: session cookie. O'zgartiruvchi so'rovlar `X-CSRFToken` header bilan yuboriladi.
- Xato formati: `{"error": {"code": "...", "message": "...", "fields": {...}}}`.

## Autentifikatsiya

Django session + CSRF (JWT yo'q). Uch yo'l:

| Yo'l | Oqim |
|---|---|
| Google | Frontend ID token (JWT) oladi → backend uni Google kalitlari bilan tekshiradi (`apps/users/social.py`) |
| Telegram | Login Widget ma'lumoti bot tokeni bilan HMAC-SHA256 orqali tekshiriladi |
| Telefon | SMS kod (`OneTimeCode`, faqat HMAC xeshi saqlanadi) + parol |

- Google yoki Telegram bilan birinchi kirishda **akkaunt darhol yaratilmaydi**: avval telefon
  raqami so'raladi (provayder ma'lumoti sessiyada 15 daqiqa turadi). Shu sabab har bir
  foydalanuvchida telefon raqami bo'ladi.
- Raqam boshqa akkauntga tegishli bo'lsa, SMS kod so'raladi va ijtimoiy akkaunt o'shanga
  bog'lanadi (`OneTimeCode.Purpose.LINK`).
- Limitlar: bitta raqamga 60 soniyada 1 kod va sutkasiga 5 kod; 10 marta noto'g'ri paroldan
  keyin raqam 15 daqiqa bloklanadi (parolni tiklash blokni ochadi). IP bo'yicha throttle
  `REST_FRAMEWORK.DEFAULT_THROTTLE_RATES` da.
- Parol o'zgarganda boshqa qurilmalardagi sessiyalar avtomatik yopiladi.

## Admin panel

- Tarjima qilinadigan maydonlar (uz/ru/en) til tablarida: `apps/core/admin_utils.py` → `language_tabs()`.
- Hero sarlavhasida `*so'z*` — saytda ajratib ko'rsatiladi. Promo video (MP4/WebM, 200 MB gacha) "Sozlamalar va hero" sahifasida yuklanadi; bo'lmasa saytda animatsion rolik chiqadi.
- Admin yozgan HTML (kurs tavsifi, huquqiy sahifalar) saqlashda `nh3` bilan tozalanadi.
- Kontent o'zgarganda `/api/v1/site/` keshi avtomatik tozalanadi (`apps/content/signals.py`).
- Audit log: katalog, kontent, arizalar va foydalanuvchilardagi har bir o'zgarish (kim, qachon, eski → yangi) — Foydalanuvchilar → Audit log.
- Namunaviy kontent: `python manage.py seed_demo` (faqat bo'sh jadvallarni to'ldiradi).
- Foydalanuvchi sahifasida uning Google/Telegram akkauntlari ko'rinadi; "SMS kodlar" jurnali faqat o'qish uchun (kodning o'zi saqlanmaydi).

## Ishga tushirish

Root papkadan `docker compose up --build` (qarang: [../README.md](../README.md)).

Docker'siz ishlash uchun [uv](https://docs.astral.sh/uv/) kerak:

```bash
uv sync
uv run python manage.py runserver
```

Bu holda `.env` da `DATABASE_URL` va `REDIS_URL` ni yozing.

## Sifat

```bash
docker compose exec backend pytest
docker compose exec backend ruff check .
docker compose exec backend ruff format .
docker compose exec backend mypy .
```

## Docker image target'lari

| Target | Nima uchun |
|---|---|
| `dev` | Local: dev bog'liqliklari, `runserver`, kod volume orqali |
| `runtime` | Production: gunicorn + uvicorn worker (ASGI), root bo'lmagan foydalanuvchi |
| `video` | `runtime` + ffmpeg (production video worker) |
| `video-dev` | `dev` + ffmpeg (local video worker, kod volume orqali) |

Entrypoint o'zgaruvchilari: `RUN_MIGRATIONS=1`, `COLLECT_STATIC=1`, `ENSURE_SUPERUSER=1` va `ENSURE_BUCKETS=1` (ikkalasi faqat local).
