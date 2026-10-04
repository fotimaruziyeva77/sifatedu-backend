# SIFAT EDU — Ish rejasi

| | |
|---|---|
| **Asos** | `TZ-umumiy.md` v2.2 |
| **Sana** | 2026-09-26 |
| **Holat** | Tasdiqlangan qarorlar: backend — Django + DRF, admin panel — Django Admin. Ish 0-qadamdan boshlanadi |

---

## 1. Asosiy qarorlar

| # | Qaror | Sabab |
|---|---|---|
| 1 | **Frontend va backend — ikkita mustaqil loyiha** (`frontend/`, `backend/`). Har birida o'z paket fayli, lockfile, `Dockerfile`, `.env.example` va README bor. Umumiy workspace yoki umumiy kod yo'q | Monorepo kerak emas. Har birini alohida git repozitoriyaga chiqarish mumkin |
| 2 | **Backend: Python 3.13 + Django 5.2 LTS + Django REST Framework** | Loyihada model va admin sahifalari ko'p: ORM, migratsiyalar va admin tayyor. 5.2 LTS 2028-yil aprelgacha qo'llab-quvvatlanadi; ba'zi kutubxonalar hali 6.x ni qo'llamaydi |
| 3 | **Admin panel (1-bosqich): Django Admin + Unfold temasi**, `/admin/` | TZ'dagi 1-bosqich admin sahifalari frontend'da yozilmaydi, vaqt 3D landing va talaba sahifalariga ketadi. Instruktor va Manager panellari 2-bosqichda frontend'da yoziladi |
| 4 | **Frontend: Next.js 16 (App Router) + Tailwind v4 + shadcn/ui + next-intl** | SEO va SSR kerak |
| 5 | **3D: React Three Fiber + drei + postprocessing**, DOM animatsiyalari — Motion (Framer Motion) | React bilan tabiiy ishlaydi, lazy yuklash oson |
| 6 | **Tiplar OpenAPI orqali:** `drf-spectacular` sxema chiqaradi, frontend `openapi-typescript` bilan tip generatsiya qiladi | Umumiy paketsiz ham tiplar sinxron turadi |
| 7 | **Bitta domen, nginx orqali:** `/` → frontend; `/api/`, `/admin/`, `/static/` → backend | Cookie va CSRF oddiy ishlaydi, CORS kerak emas |
| 8 | **Auth: Django session** (httpOnly cookie, sessiyalar Redis'da) + CSRF token. JWT ishlatilmaydi | Hammasi bitta domenda, mobil ilova rejada yo'q. Parol o'zgarsa, barcha sessiyalar avtomatik bekor bo'ladi (TZ'dagi `tokenVersion` o'rniga). Bitta login bilan sayt va admin ishlaydi |
| 9 | **Fon vazifalari: Celery + Redis**, davriy vazifalar — Celery beat | Django uchun standart |
| 10 | **Kontent tarjimasi: django-modeltranslation** (`title_uz`, `title_ru`, `title_en`) | Admin'da til tablari bor, tarjima bo'lmasa o'zbekchasi chiqadi, qidiruv oson |
| 11 | **Docker Compose:** dev uchun `docker compose up`, production uchun `-f docker-compose.yml -f docker-compose.prod.yml` | TZ talabi |
| 12 | **Avval faqat 1-bosqich (MVP)**. 2–3-bosqichlar TZ'da yo'l xaritasi bo'lib qoladi | Scope creep xavfi (TZ 17-bo'lim) |

---

## 2. Papka tuzilmasi

```
sifatedu/                          # deploy va orkestratsiya (alohida repo bo'lishi mumkin)
├── backend/                       # mustaqil Django loyiha
│   ├── Dockerfile  pyproject.toml  uv.lock  manage.py  .env.example  README.md
│   ├── config/                    # settings (base, dev, prod, test), urls, asgi, celery
│   └── apps/
│       ├── core/                  # health, umumiy modellar, xato formati, throttle'lar
│       ├── users/                 # User (telefon bilan), OTP, auth API, profil
│       ├── content/               # landing matnlari, FAQ, huquqiy sahifalar, sozlamalar
│       ├── leads/                 # arizalar
│       ├── catalog/               # kategoriya, ustoz, kurs, modul, dars, materiallar
│       ├── videos/                # VideoAsset, multipart yuklash, ffmpeg → HLS
│       ├── learning/              # enrollment, progress, playback
│       ├── payments/              # buyurtma, Click, fiskal chek, refund
│       └── notifications/         # Eskiz SMS, Telegram
├── frontend/                      # mustaqil Next.js loyiha
│   ├── Dockerfile  package.json  package-lock.json  next.config.ts  .env.example  README.md
│   ├── messages/{uz,ru,en}.json
│   ├── public/brand/              # logo.svg, og-image, 3D poster
│   └── src/
│       ├── app/[locale]/          # (public), (auth), dashboard, checkout
│       ├── components/ui/         # shadcn
│       ├── components/three/      # 3D sahnalar (faqat client, lazy)
│       ├── features/<domen>/
│       ├── i18n/
│       └── lib/api/               # API client + generatsiya qilingan tiplar
├── infra/nginx/                   # nginx konfiguratsiyasi
├── docker-compose.yml             # asosiy servislar
├── docker-compose.override.yml    # dev: hot reload, portlar (avtomatik ulanadi)
├── docker-compose.prod.yml        # prod: TLS, restart, resurs limitlari
├── .env.example                   # faqat compose uchun (DB paroli, portlar)
├── docs/                          # TZ-umumiy.md, PLAN.md
└── brand/                         # logoning asl fayli
```

> **OneDrive haqida:** loyiha OneDrive papkasida turibdi. `node_modules` va Python virtual muhiti **faqat Docker volume'larida** saqlanadi, aks holda OneDrive o'n minglab fayllarni sinxronlashga urinadi. Imkon bo'lsa, loyihani OneDrive'dan tashqariga ko'chirish tavsiya etiladi (masalan, `C:\Projects\sifatedu`).

---

## 3. Docker servislari

| Servis | Image | Vazifasi | Hostdagi port (dev) |
|---|---|---|---|
| `nginx` | nginx:alpine | Reverse proxy, static fayllar, security headerlar, HLS kesh | **80** (`HTTP_PORT`) |
| `frontend` | `./frontend` (node:24-alpine, standalone) | Next.js SSR | — |
| `backend` | `./backend` (python:3.13-slim) | Django: API + admin. Prod'da gunicorn + uvicorn worker (ASGI) | — |
| `worker` | `./backend` | Celery: SMS, Telegram, umumiy vazifalar | — |
| `beat` | `./backend` | Celery beat: davriy vazifalar (to'lanmagan buyurtmalar, eskirgan OTP) | — |
| `worker-video` | `./backend` (`video` target, ffmpeg bilan) | Celery: video → HLS. **4-qadamda qo'shiladi** | — |
| `postgres` | pgvector/pgvector:pg17 | DB (`pgvector` 2-bosqich uchun tayyor) | 15433 (`POSTGRES_PORT`) |
| `redis` | redis:7-alpine | Celery broker, kesh, sessiyalar, rate limit | — |
| `seaweedfs` | chrislusf/seaweedfs | S3-mos storage (MinIO community image'lari endi tarqatilmaydi). Production'da ham shu — serverning o'zida, `media.<domen>` orqali (18-qadam) | 9000, 8888 (faqat local) |

- Portlar kompyuterdagi boshqa loyihalar bilan to'qnashmasligi uchun tanlangan: 5432, 5433, 6379, 8000 va 8080 band edi.
- Har bir servisda `healthcheck` bor. `backend` DB va Redis tayyor bo'lgach ishga tushadi va avval `migrate` bajaradi.
- Build multi-stage, runtime'da root bo'lmagan foydalanuvchi ishlaydi, maxfiy kalitlar image ichiga kirmaydi.
- Dev rejimda kod volume orqali ulanadi (hot reload). `node_modules` va `.venv` konteyner ichida qoladi.

**Ishga tushirish (dev):**
```bash
docker compose up --build
```

| Manzil | Nima |
|---|---|
| http://localhost | Sayt |
| http://localhost/admin/ | Django Admin |
| http://localhost/api/docs/ | Swagger (API hujjati) |
| http://localhost:8888 | S3 fayl ko'ruvchisi (SeaweedFS) |

---

## 4. Dizayn va 3D konsepsiya

> 2-iteratsiya (buyurtmachi fikri asosida): birinchi variant "juda rasmiy" deb topildi. Quyidagi yo'nalish uning o'rnini egallaydi. Tafsilotlar va sabablar — 7.2-bo'limda.

### 4.1. Konsepsiya va dizayn tokenlari

**Konsepsiya: "Nuqtalarni bog'lang".** IT'ni o'rganish — tarqoq bilimlarni bir-biriga ulash. Sayt buni so'zsiz ko'rsatadi: logo nuqtalardan yig'iladi, kursor yurgan joyda nuqtalar bir-biriga ulanadi, o'qish yo'li scroll bilan chiziladi. Brend qizili — "uchqun": faol ulanishlar, CTA va kursor.

| Token | Tun | Kun | Qayerda |
|---|---|---|---|
| Fon | `#0B0D1A` | `#F6F7FC` | |
| Kartochka | `#131629` | `#FFFFFF` | |
| Asosiy matn | `#EEF0FA` | `#121427` | |
| Ikkinchi darajali matn | `#9BA1C4` | `#595F82` | Ikkala temada ham fonga nisbatan ≥ 4.5:1 |
| Brend qizil | `#E31E24` (porlash `#FF3B45`) | `#E31E24` | CTA, kursor, faol ulanishlar |
| Tarmoq chiziqlari | `#8F98FF` | `#3F47A8` | 3D va 2D tarmoq |
| Yo'nalish ranglari | Frontend `#FFBE4D`, Backend `#45DFBD`, Dizayn `#FF79B0`, IT asoslari `#67B2FF` | `#C77800`, `#0A9277`, `#D4357D`, `#1E6FD6` | Kurs kartochkasi, test natijasi, 3D tugunlar. Faqat bezak uchun, matn uchun emas |

- **Shriftlar:** sarlavhalar — **Geologica** (o'zgaruvchan; ajratilgan so'zlarda `CRSV` o'qi harflarni qo'lyozmaga yaqinlashtiradi), matn — **Onest**, raqamlar, teglar va kod — **Martian Mono**. Uchalasi ham kirill va o'zbek lotin yozuvini qo'llaydi. Oldindan faqat lotin qismi yuklanadi.
- **Tema:** kun va tun. Birinchi kirishda tizim sozlamasi olinadi, tanlov `localStorage`'da saqlanadi. Tema `<head>`'dagi inline script bilan birinchi chizishdan oldin qo'yiladi (miltillash yo'q). Almashtirganda tugmadan doira bo'lib ochiladi (View Transitions).
- **Shakl:** katta radiuslar (16–28px), yumshoq soyalar (kun) va ingichka yorug' chegaralar (tun).

### 4.2. 3D va animatsiyalar

| Joy | Nima | Texnika |
|---|---|---|
| **Hero** | SIFAT logosi nuqtalar va chiziqlardan yig'iladi, keyin "ko'nikmalar turkumi"ga aylanadi (HTML, CSS, JavaScript, Python, Figma...; har yo'nalish o'z rangida). Kursor yaqinidagi nuqtalar unga va bir-biriga ulanadi. Telefonda "arvoh kursor" o'zi aylanib, ulanishlarni ko'rsatadi | R3F: `Points` + `LineSegments`, ulanishlar CPU'da (≤ 150 tugun) |
| **Xavotirlar, yakuniy CTA** | Fonda 2D tarmoq: kursor atrofidagi nuqtalar ulanadi | Canvas 2D |
| **Biz kimmiz** | Promo video (admin yuklaydi). Video bo'lmasa — kod bilan yasalgan motion-rolik: kimmiz va nima beramiz | `<video>` yoki CSS animatsiya |
| **Yo'l (4 qadam)** | Scroll bilan chiziladigan chiziq, qadamlar navbat bilan yonadi | Scroll progress + CSS |
| **Kurslar** | Har yo'nalish uchun "nimani yasaysiz" mini-animatsiyasi, 3D tilt, kursor ostida yorug'lik | CSS |
| **Har bir kursda (bento)** | Har plitkada mini-animatsiya: video, kod yozilishi, tillar, internet tezligi... | CSS/SVG |
| **Umumiy** | Bo'limlar paydo bo'lishi, magnit tugmalar, kursor ostida yorug'lik | Bitta global IntersectionObserver + CSS o'zgaruvchilari |

### 4.3. Tezlik va accessibility qoidalari (TZ 12-bo'lim: LCP < 2.5s)

1. **LCP elementi — HTML sarlavha va 3D sahnaning statik rasmi (poster).** 3D canvas sahifa yuklangandan keyin `dynamic(..., { ssr: false })` bilan brauzer bo'shaganda yuklanadi.
2. 3D bundle ≤ 250 KB (gzip). Sahna kodda generatsiya qilinadi (logo SVG yo'llaridan nuqtalar), tashqi fayl yuklanmaydi.
3. **3D o'chadi va poster qoladi, agar:** `prefers-reduced-motion`, `Save-Data`, WebGL yo'q yoki qurilma kuchsiz bo'lsa. `PerformanceMonitor` FPS'ni kuzatadi, avval sifatni pasaytiradi, keyin 3D ni o'chiradi.
4. Canvas `aria-hidden="true"`, barcha mazmun oddiy DOM'da.
5. Sahna ekrandan chiqsa, render to'xtaydi.
6. Mobil qurilmada kamroq obyekt bo'ladi, postprocessing yo'q.
7. Animatsiya kutubxonasi ishlatilmaydi: paydo bo'lish va scroll effektlari IntersectionObserver + CSS bilan (boshlang'ich JS kichik qoladi). JS o'chiq bo'lsa ham mazmun ko'rinadi.
8. Barcha animatsiyalar `prefers-reduced-motion`'ni hurmat qiladi. Canvas'lar ekrandan chiqsa yoki tab yashirilsa, to'xtaydi.

---

## 5. Backend (Django): 1-bosqich

### 5.1. Kutubxonalar

| Vazifa | Kutubxona |
|---|---|
| API va hujjat | djangorestframework, drf-spectacular, django-filter |
| Admin | django-unfold |
| Tarjima | django-modeltranslation |
| Sozlamalar | django-environ |
| DB | PostgreSQL 17, psycopg 3, `pg_trgm` (qidiruv) |
| Kesh va sessiyalar | django-redis |
| Fon vazifalari | celery |
| Fayllar | django-storages (S3, boto3) |
| Parollar | argon2-cffi (`Argon2PasswordHasher`) |
| Audit log | django-auditlog |
| HTML tozalash | nh3 |
| Server | gunicorn + uvicorn-worker (ASGI) |
| Monitoring | sentry-sdk |
| Sifat | pytest, pytest-django, factory-boy, ruff, mypy + django-stubs |
| Paket menejer | uv (`pyproject.toml` + `uv.lock`) |

### 5.2. App'lar va endpointlar (`/api/v1/`)

| App | Vazifasi | Endpointlar |
|---|---|---|
| `core` | Health, xato formati `{ error: { code, message } }`, pagination, throttle'lar | `GET /health/` |
| `users` | Telefon + SMS + parol, session, parolni tiklash, profil | `GET /auth/csrf/`, `POST /auth/otp/`, `/auth/register/`, `/auth/login/`, `/auth/logout/`, `/auth/password/reset/`, `GET/PATCH /me/`, `POST /me/password/` |
| `content` | Landing matnlari, sozlamalar, FAQ, afzalliklar, qadamlar, fikrlar, huquqiy sahifalar | `GET /site/` (landing uchun hammasi bitta so'rovda, keshlangan), `GET /pages/{slug}/` |
| `leads` | Ariza: honeypot, rate limit, bir raqamdan kelgan takroriy arizalarni birlashtirish, UTM. Telegram'ga Celery orqali | `POST /leads/` |
| `catalog` | Kategoriya, ustoz, kurs, modul, dars, materiallar; filtr va qidiruv | `GET /categories/`, `GET /courses/`, `GET /courses/{slug}/` |
| `videos` | Presigned multipart yuklash (admin uchun), ffmpeg → HLS + AES-128 | `POST /admin/uploads/...` (faqat xodimlar) |
| `learning` | Enrollment, progress (≥ 90% = tugatilgan), playback, AES kaliti | `GET /my/courses/`, `GET /lessons/{id}/`, `GET /lessons/{id}/playback/`, `GET /videos/{id}/key/`, `PUT /lessons/{id}/progress/` |
| `payments` | Buyurtma (summa serverda), Click Prepare/Complete, fiskal chek, refund | `POST /orders/`, `GET /orders/`, `GET /orders/{id}/`, `POST /payments/click/prepare/`, `/complete/` |
| `notifications` | Eskiz SMS (`SMS_DRY_RUN` rejimi), Telegram | Faqat ichki servis va Celery vazifalari |

### 5.3. Django Admin (Unfold) — 1-bosqich admin sahifalari

| TZ talabi | Admin'da qanday bo'ladi |
|---|---|
| Dashboard | Bugungi arizalar, to'lovlar, oylik tushum, faol talabalar |
| Kurslar, kategoriyalar, darslar | Kurs → modullar → darslar, tartiblash, 3 til tablari |
| Video | Dars formasida yuklash vidjeti: to'g'ridan-to'g'ri storage'ga multipart, progress bar, holat (`PROCESSING` / `READY`) |
| Foydalanuvchilar | Bloklash, qo'lda kursga kirish berish |
| Buyurtmalar va refund | Filtrlar, "Refund" amali (sabab bilan) |
| Arizalar | Holat, izoh, CSV eksport |
| Sayt kontenti | Sozlamalar, hero, afzalliklar, qadamlar, FAQ, fikrlar, huquqiy sahifalar |
| Audit log | django-auditlog: kim, qachon, qaysi maydonni o'zgartirgan (eski → yangi) |

**Himoya:** admin'ga faqat xodimlar kiradi, nginx'da login uchun rate limit bor. 2FA (django-otp) 2-bosqichda qo'shiladi.

### 5.4. Auth oqimi

1. Frontend `GET /auth/csrf/` orqali `csrftoken` cookie oladi va har bir o'zgartiruvchi so'rovda `X-CSRFToken` header yuboradi.
2. **Ro'yxatdan o'tish:** `POST /auth/otp/` {telefon, `register`} → SMS (dev'da kod konsolga chiqadi) → `POST /auth/register/` {telefon, kod, parol, ism, familiya} → session ochiladi.
3. **Kirish va chiqish:** `POST /auth/login/`, `POST /auth/logout/`.
4. **Parolni tiklash:** `POST /auth/otp/` {`reset`} → `POST /auth/password/reset/`.
- **OTP:** 6 raqam, DB'da hash, 5 daqiqa amal qiladi, 5 urinish. Bitta raqamga 60 soniyada 1 marta, kuniga ko'pi bilan 5 ta; IP bo'yicha ham limit bor.
- **Session:** Redis'da, 30 kun; cookie httpOnly, `Secure` (prod), `SameSite=Lax`.

### 5.5. Video himoyasi (4-qadam)

- Admin videoni to'g'ridan-to'g'ri storage'ga yuklaydi (presigned multipart, 2 GB gacha).
- `worker-video`: ffmpeg → HLS 360/480/720/1080 (manba sifatidan oshmaydi), har bir video uchun alohida AES-128 kaliti, thumbnail va davomiylik.
- **Playback:** backend har bir foydalanuvchi uchun playlist beradi, undagi segment URL'lari qisqa muddatli imzolangan. Kalit `/api/v1/videos/{id}/key/` orqali faqat ruxsati borlarga beriladi.
- Pleyer ustida foydalanuvchi ID'si bilan harakatlanuvchi watermark bo'ladi.

### 5.6. To'lov (5-qadam)

- `POST /orders/`: summa serverda hisoblanadi, javobda Click to'lov sahifasi havolasi qaytadi.
- **Click Prepare/Complete:** MD5 imzo va summa tekshiriladi. Idempotentlik uchun `click_trans_id` unikal. Tranzaksiya ichida `select_for_update` ishlatiladi. Barcha so'rov va javoblar `PaymentLog`'ga yoziladi.
- Celery beat 30 daqiqada to'lanmagan buyurtmani `EXPIRED` qiladi.
- **Fiskal chek:** Click fiskalizatsiya API orqali (protokol rasmiy hujjat bo'yicha tekshiriladi), MXIK kodi kursda saqlanadi.
- Kurs faqat muvaffaqiyatli `Complete`'dan keyin ochiladi.

---

## 6. Frontend: 1-bosqich sahifalari

| Guruh | Sahifalar |
|---|---|
| Ommaviy | Landing (3D), `/courses`, `/courses/[slug]`, preview dars, `/about`, `/contacts`, `/offer`, `/privacy`, `/refund-policy` |
| Auth | `/auth/login`, `/auth/register`, `/auth/forgot-password` |
| O'quvchi | `/dashboard`, `/dashboard/courses`, dars sahifasi (hls.js pleyer, watermark), `/dashboard/orders`, `/dashboard/settings`, `/checkout/...`, `/payment/result` |

- **Ma'lumot olish:** Server Components'da backend'ga `fetch` (Docker tarmog'i ichida, cookie uzatiladi), client'da TanStack Query.
- **Route himoyasi:** Next.js `proxy.ts` session cookie borligini tekshiradi; haqiqiy tekshiruv backend'da.
- **SEO:** `hreflang`, Open Graph, `sitemap.xml`, JSON-LD.
- **Admin sahifalari frontend'da yo'q**, ular Django Admin'da.

---

## 7. Bajarish tartibi (1-bosqich)

Har bir qadam oxirida hammasi Docker'da ishga tushiriladi va tekshiriladi.

| # | Qadam | Natija | Tekshiruv |
|---|---|---|---|
| **0** ✅ | **Asos:** papkalar, Django va Next.js loyihalari, Dockerfile'lar, compose (dev + prod), nginx, healthcheck, lint, `.env.example`, Unfold admin | `docker compose up` bilan sayt, admin va Swagger ochiladi | Barcha konteynerlar `healthy` |
| **1** ✅ | **Brend + 3D landing + arizalar:** logo SVG, dizayn tokenlari, landing (3 til), landing kontenti admin'da, ariza DB'ga va Telegram'ga | Landing tayyor, matnlar admin'dan tahrirlanadi | **Siz brauzerda ko'rib chiqasiz va tasdiqlaysiz.** Lighthouse Perf ≥ 85, ariza ≤ 10 soniyada |
| **2** ✅ | **Auth + profil** | Google, Telegram va telefon + SMS + parol; parolni tiklash, kabinet va sozlamalar | pytest (143 ta test) |
| **3** ✅ | **Katalog + kurs sahifasi + admin'da kurslar** | Admin kurs, modul va dars yaratadi; ular katalogda va kurs sahifasida chiqadi | Filtr, qidiruv va saralash testlari (165 ta test) |
| **4** ✅ | **Video + pleyer + progress + ikki kabinet** | Video yuklanadi va `READY` bo'ladi; himoyalangan HLS; progress saqlanadi; kabinet kattalar va SIFAT Kids ko'rinishida | Sotib olinmagan video URL orqali ochilmaydi (test bilan qoplangan) |
| **5** ✅ | **Click + checkout + fiskal + buyurtmalar va refund admin'da + audit log** | To'lovdan keyin kurs ochiladi | Click'ning barcha holatlari testda (imzo, summa, idempotentlik, bekor qilish, muddat) |
| **6** ✅ | **Sifat va production:** E2E, axe-core, Sentry, backup skripti, security headerlar, CI, prod compose | Production'ga tayyor | 16 ta E2E (to'lov oqimi bilan), axe, CSP, `check --deploy`, backup/tiklash sinovi; Lighthouse — 7.9-bo'lim |

### 7.1. 1-qadam: batafsil vazifalar

**Backend**

| # | Vazifa |
|---|---|
| 1 | `content` app: `SiteSettings` (yagona yozuv: kontaktlar, ijtimoiy tarmoqlar, hero matnlari, bo'limlarni yoqish/o'chirish), `Advantage`, `HowStep`, `FAQItem`, `Testimonial`, `LegalPage`. Tarjima — modeltranslation, admin'da til tablari |
| 2 | `GET /api/v1/site/` — landing uchun barcha ma'lumot bitta so'rovda (Redis'da keshlanadi, admin'da saqlanganda kesh tozalanadi); `GET /api/v1/pages/{slug}/` — huquqiy sahifalar |
| 3 | `catalog` app'ning boshlang'ich qismi: `Category`, `Instructor`, `Course` (asosiy maydonlar va `is_featured`) — landing'dagi kurslar va ustozlar bo'limlari uchun. Modul, dars va kurs sahifasi 3-qadamda |
| 4 | `leads` app: `POST /api/v1/leads/` — honeypot, IP bo'yicha limit, bitta raqamdan 24 soat ichida kelgan takroriy arizani birlashtirish, UTM va manba sahifa. Admin: holat, izoh, CSV eksport |
| 5 | `notifications` app: Telegram mijozi va Celery vazifasi (qayta urinish bilan). Token berilmagan bo'lsa, faqat logga yoziladi |
| 6 | `seed_demo` buyrug'i: 3 tildagi namunaviy matnlar, kurslar va ustozlar (landing'ni ko'rib chiqish uchun) |
| 7 | Testlar: ariza (validatsiya, honeypot, birlashtirish, limit), `/site/` (til, kesh) |

**Frontend**

| # | Vazifa |
|---|---|
| 1 | Logo: SVG wordmark va belgi (favicon) — asl rasm o'lchamlari asosida |
| 2 | shadcn/ui komponentlari, ranglar brend tokenlariga moslanadi |
| 3 | Layout: header (menyu, til almashtirgich, "Bepul maslahat" tugmasi), footer (kontaktlar, ijtimoiy tarmoqlar, huquqiy havolalar). "Kirish" tugmasi 2-qadamda qo'shiladi |
| 4 | Landing bo'limlari: hero (3D), raqamlar, kurslar, afzalliklar, "Qanday ishlaydi", ustozlar, fikrlar (bo'lsa), FAQ, ariza formasi |
| 5 | 3D sahna: SVG'dan hajmli logo, porlovchi qizil chiziq, suzuvchi shakllar, perspektiv to'r, sichqoncha parallaksi, scroll bilan kamera. Lazy yuklanadi; poster, `prefers-reduced-motion` va kuchsiz qurilma uchun zaxira variant |
| 6 | Ariza formasi: React Hook Form + Zod, +998 maskasi, honeypot, UTM saqlash, natija xabari |
| 7 | Huquqiy sahifalar: `/offer`, `/privacy`, `/refund-policy` (matn admin'dan) |
| 8 | SEO: 3 tilda metadata, `hreflang`, Open Graph, `sitemap.xml`, `robots.txt`, JSON-LD |

**Tekshiruv:** Lighthouse (mobil), ariza admin'ga (va token bo'lsa Telegram'ga) tushadi, 3 til, klaviatura bilan to'liq navigatsiya.


### 7.2. 1-qadam, 2-iteratsiya: landing redizayni

**Buyurtmachi fikri:** (1) juda rasmiy; (2) kreativ, animatsiyali, video bo'lsin — kimmiz va nima bera olamiz; (3) kun/tun rejimi, bir-biriga bog'langan yoqimli shrift va ranglar, odamni saytda ushlab qolish, "senior darajasi" sezilsin; (4) kursor yurganda narsalar bir-biriga ulansin; (5) sayt odamni psixologik jihatdan "nega aynan biz" degan xulosaga olib borsin. Ekrandagi xato: 3D logo ruscha sarlavhaning ustiga tushib qolgan.

**Sahifa hikoyasi** (StoryBrand: mijoz — qahramon, biz — yo'lboshchi):

| # | Bo'lim | Vazifasi |
|---|---|---|
| 1 | **Hero** | Orzu va aniq taklif: "Kelajagingizni *kod* bilan yozing". CTA: bepul maslahat va "Qaysi kasb menga mos?" testi. Pastda faqat haqiqiy raqamlar |
| 2 | **Sizga ham tanishmi?** | Empatiya: odamni to'xtatadigan xavotirlar ("qayerdan boshlashni bilmayman", "ingliz tilini bilmayman"...) va har biriga aniq javob |
| 3 | **Biz kimmiz** | Yo'lboshchi: promo video yoki motion-rolik, manifest (scroll bilan so'zma-so'z yonadi), ustozlar |
| 4 | **Yo'l** | Aniq reja — 4 qadam, scroll bilan chiziladi: noaniqlik qo'rquvini kamaytiradi |
| 5 | **Kurslar + kasb testi** | Tanlov va shaxsiylashtirish: 3 savol → mos kurs va haftasiga ajratiladigan vaqtga qarab taxminiy muddat |
| 6 | **Har bir kursda** | Foyda (bento): video darslar, amaliyot, 3 til, sekin internet, umrbod kirish |
| 7 | **Fikrlar** | Ijtimoiy isbot. Faqat haqiqiy fikrlar, bo'lmasa bo'lim yashirin |
| 8 | **Kafolatlar + FAQ** | E'tirozlarga javob: majburiyatsiz maslahat, Click orqali xavfsiz to'lov, pulni qaytarish qoidalari |
| 9 | **Birinchi qadam** | Kichik majburiyat: bepul suhbat formasi. Muvaffaqiyatda nuqtalar belgi bo'lib ulanadi |

Barcha va'dalar platformaning 1-bosqichdagi haqiqiy imkoniyatlariga tayanadi (AI yordamchi, sertifikat va jonli chat keyingi bosqichlarda bo'lgani uchun landingda aytilmaydi).

**Backend**

| # | Vazifa |
|---|---|
| 1 | `Concern` modeli ("Xavotirlar": xavotir → javob), 3 tilda, admin'da til tablari va tartiblash |
| 2 | `SiteSettings`: `about_text` (manifest, 3 tilda), `promo_video` (MP4/WebM, ≤ 200 MB, ochiq bucket), `promo_poster`. Hero sarlavhasida `*so'z*` — ajratib ko'rsatiladigan so'z |
| 3 | `/api/v1/site/` javobiga `concerns`, `about_text`, `promo_video`, `promo_poster` qo'shiladi |
| 4 | nginx: admin orqali video yuklash uchun `client_max_body_size` faqat `/admin/` da 200 MB |
| 5 | `seed_demo`: yangi matnlar (3 tilda). Testlar |

**Frontend**

| # | Vazifa |
|---|---|
| 1 | Tokenlar (kun/tun), shriftlar, tema tugmasi (View Transitions), miltillashsiz tema script |
| 2 | Global o'zaro ta'sirlar: paydo bo'lish, kursor ostida yorug'lik, magnit tugmalar — bitta client komponent, bo'limlar server komponent bo'lib qoladi |
| 3 | Hero: yangi 3D sahna ("nuqtalardan logo → ko'nikmalar turkumi", kursor ulanishlari), nuqtali logo posteri (SSR, 3D bo'lmasa shu qoladi), matn 3D bilan to'qnashmaydigan joylashuv |
| 4 | 2D tarmoq komponenti, motion-rolik va video pleyer, kasb testi, yo'l, bento va kurs mini-animatsiyalari |
| 5 | Header menyusi yangi bo'limlarga moslanadi; footer yangilanadi; barcha matnlar 3 tilda |

**Sizdan kerak (ijtimoiy kirish uchun):** Google Cloud Console'da OAuth client ID (Web), ruxsat etilgan manbalar ro'yxatiga sayt manzili; Telegram bot nomi va @BotFather'da `/setdomain`. Ikkalasi ham bepul.

**Sizdan kerak:** promo video (1–2 daqiqa, 1080p, MP4, ≤ 200 MB — admin'dan yuklanadi), ustozlarning rasmlari, manifest va xavotirlar matnining yakuniy varianti (hozirgisi namunaviy).

**Tekshiruv:** 2 tema × 3 til × desktop/telefon, `prefers-reduced-motion`, klaviatura, Lighthouse, 3D bundle ≤ 250 KB.


### 7.3. 2-qadam: auth va profil — batafsil vazifalar

Landing dizayni 2026-09-27 da tasdiqlandi. 2-qadam shu kuni bajarildi (143 backend testi).

**Oqimlar**

Ikki yo'l: **Google/Telegram** (bir bosishda, SMSsiz — asosiy yo'l) va **telefon + parol** (Google'i yo'qlar uchun).

| Oqim | Qadamlar |
|---|---|
| Google yoki Telegram | Tugma → provayder tokeni tekshiriladi → akkaunt tanish bo'lsa darhol kiradi; yangi bo'lsa telefon raqami so'raladi (SMSsiz, chunki provayder allaqachon tasdiqlagan) → akkaunt yaratiladi |
| Ijtimoiy kirishda raqam band | Raqam boshqa akkauntga tegishli bo'lsa: SMS kod → kod tasdiqlansa, Google/Telegram o'sha akkauntga bog'lanadi (egalik isboti) |
| Ro'yxatdan o'tish (telefon) | Telefon → SMS kod → kod + ism + familiya + parol + oferta va maxfiylik siyosatiga rozilik → session ochiladi → kabinet |
| Kirish (telefon) | Telefon + parol → kabinet (yoki `?next=` dagi sahifa). Kirishdan so'ng interfeys foydalanuvchi tanlagan tilga o'tadi |
| Parolni tiklash | Telefon → SMS kod → kod + yangi parol → barcha boshqa sessiyalar bekor bo'ladi → kabinet |
| Profil | Ism, familiya, rasm, interfeys tili; parolni o'zgartirish (joriy sessiya qoladi, boshqalari chiqadi); chiqish |

**Ijtimoiy kirish qoidalari**

- **Google:** frontend Google Identity Services orqali ID token (JWT) oladi, backend uni Google'ning ochiq kalitlari bilan tekshiradi (imzo, `aud`, `iss`, muddat, `email_verified`). Parol saqlanmaydi.
- **Telegram:** Login Widget ma'lumotlari bot tokeni bilan HMAC-SHA256 orqali tekshiriladi; `auth_date` 5 daqiqadan eski bo'lsa rad etiladi. Widget uchun bot domeni @BotFather'da sozlanadi — shu sababli `localhost`da sinab bo'lmaydi. Widget **`data-auth-url`** rejimida: kirgach `/auth/telegram` qaytish sahifasiga yo'naltiradi (`data-onauth` ishlatilmaydi — widget uni `eval` bilan chaqiradi, CSP esa taqiqlaydi).
- Akkaunt `(provayder, uid)` bo'yicha topiladi. Yangi foydalanuvchi telefon so'ralgunga qadar **yaratilmaydi**: provayder ma'lumotlari sessiyada 15 daqiqa turadi. Shu sabab telefon maydoni majburiy bo'lib qoladi.
- Provayder bergan ism va rasm faqat bo'sh maydonlarga yoziladi: foydalanuvchi o'zgartirgan ma'lumot ustiga yozilmaydi.
- Sozlanmagan provayder tugmasi saytda ko'rinmaydi (`GOOGLE_CLIENT_ID` yoki bot nomi bo'lmasa).

**Backend**

| # | Vazifa |
|---|---|
| 1 | `OneTimeCode` modeli: telefon, maqsad (`register` / `reset`), kod xeshi (HMAC, `SECRET_KEY` bilan), urinishlar, muddat, ishlatilgan vaqti, IP. Kod 6 raqam, 5 daqiqa, 5 urinish, bir marta ishlatiladi |
| 2 | Limitlar: bitta raqamga 60 soniyada 1 kod, sutkasiga 5 kod; IP bo'yicha OTP, kirish va tasdiqlash so'rovlari cheklangan. 10 marta noto'g'ri paroldan keyin raqam 15 daqiqa bloklanadi (parolni tiklash blokni ochadi) |
| 3 | Endpointlar: `GET /auth/csrf/`, `POST /auth/otp/`, `/auth/register/`, `/auth/login/`, `/auth/logout/`, `/auth/password/reset/`, `GET/PATCH /me/` (rasm — multipart, 2 MB gacha), `POST /me/password/`. Kirish/ro'yxat/tiklash CSRF bilan himoyalangan |
| 4 | Akkaunt borligini oshkor qilmaslik: kirish xatosi umumiy ("telefon yoki parol noto'g'ri"), parolni tiklashda noma'lum raqamga ham bir xil javob (SMS yuborilmaydi) |
| 5 | SMS: Eskiz.uz mijozi (token keshlanadi, 401 da yangilanadi), Celery orqali qayta urinish bilan. `SMS_DRY_RUN=true` da SMS yuborilmaydi — matn worker logiga yoziladi (local sinov uchun) |
| 6 | `User`: rasm (ochiq bucket, tasodifiy nom), oferta va maxfiylik siyosati qabul qilingan vaqt va versiyalar. Yangi foydalanuvchi "Talaba" guruhiga qo'shiladi |
| 7 | Admin: foydalanuvchida rasm va rozilik ma'lumotlari; "SMS kodlar" jurnali (faqat o'qish uchun, kodning o'zi ko'rinmaydi) |
| 8 | `SocialAccount` modeli: provayder, `uid`, email, bog'langan sana. `(provayder, uid)` yagona. Endpointlar: `POST /auth/social/{google,telegram}/` → `{"status": "ok"}` yoki `{"status": "phone_required"}`; `POST /auth/social/phone/` (raqam + kerak bo'lsa SMS kod) |
| 9 | `OneTimeCode.Purpose.LINK`: ijtimoiy akkauntni mavjud (band raqamli) akkauntga bog'lash uchun SMS |
| 10 | Testlar: OTP (limitlar, muddat, urinishlar, qayta ishlatish), ro'yxat, kirish, blok, chiqish, tiklash, CSRF, profil, rasm validatsiyasi, parol o'zgarganda boshqa sessiyalar chiqishi; Google tokeni (yaroqsiz imzo, boshqa `aud`, eskirgan), Telegram imzosi (buzilgan hash, eski `auth_date`), telefon band holati |

**Frontend**

| # | Vazifa |
|---|---|
| 1 | Layout'lar route group'larga bo'linadi: `(site)` — header va footer, `(auth)` — soddalashtirilgan sahifa, `(app)` — kabinet |
| 2 | `/auth/login`, `/auth/register`, `/auth/forgot-password`: yuqorida Google va Telegram tugmalari, ostida "yoki telefon bilan". +998 maskasi, SMS kod maydoni (`one-time-code` avtoto'ldirish), qayta yuborish taymeri, parolni ko'rsatish, xatolar maydonlar ostida. Fonda 2D tarmoq |
| 2a | `/auth/phone`: ijtimoiy kirishdan keyingi telefon qadami (raqam band bo'lsa — SMS kod). Faqat sessiyada kutayotgan provayder ma'lumoti bo'lsa ochiladi |
| 3 | `/dashboard` (salomlashish, "Kurslarim" bo'sh holati — kurslar 3–4-qadamda) va `/dashboard/settings` (profil, rasm, til, parol, chiqish) |
| 4 | Header: "Kirish" tugmasi; kirgan foydalanuvchida rasm va menyu (Kabinet, Sozlamalar, Chiqish). Foydalanuvchi serverda `/me/` orqali olinadi — miltillash yo'q |
| 5 | `proxy.ts`: session cookie bo'lmasa `/dashboard` → `/auth/login?next=...`. Haqiqiy tekshiruv serverda (`/me/`) |
| 6 | CSRF: token cookie bo'lmasa client avval `/auth/csrf/` ni chaqiradi |

**Tekshiruv:** pytest (auth va profil), 3 tilda brauzerda qo'lda tekshiruv. Playwright E2E 6-qadamdagi umumiy E2E to'plamiga o'tkaziladi: brauzer image'lari og'ir, bu kompyuterda Docker xotirasi cheklangan.


### 7.4. 3-qadam: katalog va kurs sahifasi — batafsil vazifalar

2026-09-27 da bajarildi.

**Kontent tuzilmasi** (TZ 4.3): Kategoriya → Kurs → **Modul** → **Dars**. Modul va dars shu
qadamda qo'shiladi; video, materiallar va progress 4-qadamda.

**Backend**

| # | Vazifa |
|---|---|
| 1 | `Module` (kurs, sarlavha, tartib) va `Lesson` (modul, sarlavha, tartib, davomiyligi, `is_preview`, qisqa tavsif) modellari. Ikkalasi ham 3 tilda. Kurs dasturi admin'da modul ichida darslar ko'rinishida tahrirlanadi |
| 2 | `Course` ga hisoblanadigan maydonlar: darslar soni va umumiy davomiylik. Ular dars saqlanganda yangilanadi (signal), shunda katalogda har kurs uchun qo'shimcha so'rov bo'lmaydi |
| 3 | `GET /categories/` — kategoriyalar va har birida nechta nashr qilingan kurs borligi |
| 4 | `GET /courses/` — filtr (`category`, `level`, `video_language`, `is_free`, `price_min`, `price_max`), qidiruv (`q` — nom va qisqa tavsif bo'yicha, joriy til va o'zbekcha maydonlarda), saralash (`popular`, `new`, `price`, `-price`), sahifalash. Faqat `PUBLISHED` |
| 5 | `GET /courses/{slug}/` — to'liq ma'lumot: tavsif, dastur (modullar va darslar), ustozlar, narx, daraja, video tili, davomiyligi. Nashr qilinmagan kurs — 404 |
| 6 | Qidiruvni tezlashtirish uchun `pg_trgm` kengaytmasi va GIN indekslar (migratsiyada) |
| 7 | Admin: kurs ichida modullar, modul ichida darslar (inline), tartibni sichqoncha bilan o'zgartirish; "Kurslar" ro'yxatida darslar soni va davomiyligi |
| 8 | `seed_demo`: har bir namunaviy kursga 3–4 modul va 12–18 dars (3 tilda), birinchi dars — bepul |
| 9 | Testlar: filtr, qidiruv, saralash, sahifalash, faqat nashr qilinganlar, kurs sahifasi, hisoblanadigan maydonlar |

**Frontend**

| # | Vazifa |
|---|---|
| 1 | `/courses` — katalog: qidiruv, kategoriya va daraja filtrlari, saralash, kartalar to'ri, sahifalash. Filtrlar URL'da (`?category=frontend&level=BEGINNER`) — havolani ulashish va SEO uchun. Server komponent: filtr o'zgarganda sahifa serverdan qayta keladi |
| 2 | `/courses/[slug]` — kurs sahifasi: sarlavha, qisqa tavsif, narx va CTA (yuqorida "yopishib" turadigan panel), to'liq tavsif, dastur (modullar akkordeoni, bepul darslar belgilangan), ustozlar, "nima o'rganasiz" |
| 3 | Kurs kartasi landing bilan umumiy (`features/landing/course-card.tsx` → umumiy joyga ko'chiriladi) |
| 4 | Landing'dagi "Kurslar" bo'limida "Barcha kurslar" tugmasi; header menyusidagi "Kurslar" endi `/courses` ga olib boradi |
| 5 | SEO: kurs sahifasi uchun metadata va JSON-LD (`Course`), katalog uchun metadata, `sitemap.xml` ga kurslar qo'shiladi |
| 6 | Kurs sahifasidagi CTA hozircha ariza formasiga olib boradi (kursni oldindan tanlaydi). To'lov 5-qadamda ulanadi |

**Chegaralar:** dars sahifasi, video, materiallar va progress — 4-qadam; sharhlar, reyting va o'quv yo'llari — 2-bosqich (TZ 4.3).

**Tekshiruv:** pytest; brauzerda 3 tilda katalog va kurs sahifasi, filtrlar va qidiruv.


### 7.5. 4-qadam: video, dars sahifasi va progress — batafsil vazifalar

Eng murakkab qadam: video yuklash, qayta ishlash, himoya va pleyer.

**Video yo'li**

1. Admin video faylni tanlaydi → backend **presigned multipart** ma'lumot beradi → brauzer faylni
   to'g'ridan-to'g'ri storage'ga yuklaydi (backend orqali o'tmaydi, 2 GB gacha).
2. Yuklash tugagach `VideoAsset` `PROCESSING` bo'ladi va `video` navbatiga vazifa tushadi.
3. `worker-video` (ffmpeg): davomiylik va thumbnail, so'ng HLS 360/480/720/1080 (manba
   sifatidan oshmaydi), **AES-128** bilan shifrlangan segmentlar. Natija storage'ga yuklanadi,
   holat `READY` bo'ladi. Xatoda `FAILED` va sabab admin'da ko'rinadi.
4. O'quvchi darsni ochganda backend **playlist'ni har safar qayta yasaydi**: segment havolalari
   qisqa muddatli imzolangan (TTL `HLS_SIGNED_URL_TTL_SEC`), kalit havolasi esa
   `/api/v1/videos/{id}/key/` — u faqat kursga kirish huquqi borlarga kalitni beradi.

**Backend**

| # | Vazifa |
|---|---|
| 1 | `videos` app: `VideoAsset` (holat, manba kaliti, HLS yo'li, davomiylik, thumbnail, o'lcham, xato matni) va AES kaliti. Kalit bazada **shifrlangan** holda saqlanadi (Fernet, `SECRET_KEY`dan olingan kalit bilan): baza sizib chiqsa ham videolar ochilmaydi |
| 2 | `Lesson.video` — darsga video biriktiriladi. Dars davomiyligi video davomiyligidan avtomatik olinadi |
| 3 | Yuklash endpointlari (faqat xodimlar): `POST /admin/uploads/start/`, `/admin/uploads/part/`, `/admin/uploads/complete/`, `/admin/uploads/abort/` — presigned multipart |
| 4 | `worker-video` servisi: `video` navbati, `--concurrency 1` (ffmpeg og'ir). ffmpeg buyruqlari: `ffprobe` bilan davomiylik, thumbnail, so'ng HLS variantlari |
| 5 | `learning` app: `Enrollment` (foydalanuvchi, kurs, manba: `PAYMENT`/`MANUAL`, holat) va `LessonProgress` (pozitsiya, tugatilgan). Dars ≥ 90% ko'rilsa tugatilgan hisoblanadi |
| 6 | Kirish qoidasi: dars ochiq, agar (a) `is_preview` bo'lsa yoki (b) foydalanuvchida shu kursga faol `Enrollment` bo'lsa. Xodimlar hammasini ko'radi. Qoida bitta joyda (`apps/learning/access.py`) va testlar bilan qoplanadi |
| 7 | Endpointlar: `GET /my/courses/`, `GET /lessons/{id}/`, `GET /lessons/{id}/playback/` (imzolangan playlist), `GET /videos/{id}/key/` (AES kaliti), `PUT /lessons/{id}/progress/` |
| 8 | Admin: kursga qo'lda kirish berish (`Enrollment`), video holati va xatolar, "qayta ishlash" tugmasi |
| 9 | Testlar: kirish qoidasi (preview, sotib olmagan, sotib olgan, xodim), progress (90%), playlist va kalitga ruxsatsiz kirish, multipart yuklash oqimi, ffmpeg chaqiruvlari (mock) |

**Frontend**

| # | Vazifa |
|---|---|
| 1 | Dars sahifasi `/dashboard/courses/[slug]/lessons/[id]`: hls.js pleyer, darslar ro'yxati (sidebar), "oldingi/keyingi", materiallar |
| 2 | Pleyer: sifat tanlash, tezlik 0.5x–2x, to'liq ekran, klaviatura (bo'shliq, ←/→, ↑/↓, F, M), oxirgi pozitsiyadan davom etish |
| 3 | Progress: har 15 soniyada va pauza/chiqishda saqlanadi (`sendBeacon`), 90% da tugatilgan |
| 4 | Foydalanuvchi ID'si bilan harakatlanuvchi watermark (pleyer ustida CSS qatlami) |
| 5 | `/dashboard/courses` — mening kurslarim: progress va "davom ettirish" |
| 6 | Bepul dars `/courses/[slug]/preview/[lessonId]` — kirmagan foydalanuvchi ham ko'radi |

**Chegaralar:** subtitrlar, transkript, AI chat va savol-javob — 2/3-bosqich. Watermark video ichiga
kuydirilmaydi (har foydalanuvchi uchun alohida transcoding juda qimmat) — u pleyer ustida chiqadi.

**Dev muhit:** ffmpeg og'ir, bu kompyuterda Docker xotirasi cheklangan — video worker'i bitta
jarayonda ishlaydi va sinov uchun qisqa, kichik videolar ishlatiladi.

**Tekshiruv:** pytest; admin'dan kichik video yuklab, `READY` bo'lishini va darsda o'ynashini
brauzerda ko'rish; sotib olmagan foydalanuvchi uchun 403.


### 7.6. Yangi talablar (2026-09-27) va ularning ta'siri

Buyurtmachi kurslar ro'yxatini va ikki muhim qoidani berdi. Bu 4-qadamni to'xtatmaydi, lekin
katalog modelini va kabinetni o'zgartiradi — shuning uchun avval model, keyin video.

**Kurslar ro'yxati (hozircha 8 ta, keyin qo'shiladi)**

| Kurs | Yo'nalish | Yosh |
|---|---|---|
| SIFAT Kids | Bolalar uchun | 7–11 |
| Kompyuter savodxonligi | Kompyuter savodxonligi | 15+ |
| Frontend | Dasturlash | 15+ |
| Backend | Dasturlash | 15+ |
| Sun'iy intellekt | Dasturlash | 15+ |
| Praktikum Frontend | Praktikum | 15+ |
| Praktikum Backend | Praktikum | 15+ |
| Ingliz tili | Til kurslari | 15+ |

**Narx modeli: onlayn va offlayn**

Bir kursning ikki shakli bo'ladi va narxlari boshqacha:

* **onlayn** — bir martalik to'lov, butun kursga kirish ochiladi;
* **offlayn** — oyma-oy to'lov (abonement), to'lov to'xtasa kirish ham to'xtaydi.

Shu sababli `Course.price` bittalik maydon bo'lib qolmaydi:

| Maydon | Ma'nosi |
|---|---|
| `study_format` | `ONLINE`, `OFFLINE` yoki `BOTH` — kurs qaysi shaklda o'qitiladi |
| `price_online` | onlayn uchun bir martalik narx |
| `price_offline_monthly` | offlayn uchun bir oylik narx |
| `is_free` | bepul kurs: to'lovsiz o'qiladi (faqat ro'yxatdan o'tish kerak) |

`Enrollment` ham shaklni biladi (`format`) va oylik to'lov uchun `expires_at` ishlatiladi:
offlayn o'quvchining kirishi to'langan oy tugagach yopiladi. Bepul kursga `Enrollment`
o'quvchining o'zi "Boshlash" tugmasi bilan ochiladi (to'lov shart emas).

**Ikki kabinet**

Kabinet bitta emas, ikkita ko'rinishda ishlaydi:

| Ko'rinish | Kimga | Qanday |
|---|---|---|
| Asosiy kabinet | 15 yoshdan kattalarga | Chap tomonda menyu (sidebar): asosiy, kurslarim, dars, to'lovlar, profil. Jiddiy, tinch uslub |
| SIFAT Kids kabineti | 7–11 yoshli o'quvchilarga | Bolalarga mos kreativ ko'rinish: yirik ranglar, belgilar, yulduz/medal bilan progress, kam matn |

Ko'rinish `User.audience` (`ADULT` / `KIDS`) bo'yicha tanlanadi. Qiymat ro'yxatdan o'tishda
so'raladi (bolaning ota-onasi ham ro'yxatdan o'tishi mumkin) va admin paneldan o'zgartiriladi.
Ikkala kabinet ham bitta `/dashboard` manzilida, lekin layout va uslub boshqa.

**Katalogda o'zgarish:** filtrlarga "kimga" (kattalar / bolalar), "shakl" (onlayn / offlayn) va
"bepul" qo'shiladi; kartochkada narx shaklga qarab ko'rsatiladi ("bir marta" yoki "oyiga").


### 7.7. 5-qadam: Click to'lovlari — batafsil vazifalar

Pul bilan ishlaydigan qadam, shuning uchun qoidalar qat'iy: **summa faqat serverda**
hisoblanadi, kurs esa **faqat Click tasdig'idan keyin** ochiladi (return URL isbot emas).

**To'lov yo'li**

1. O'quvchi kurs sahifasida shaklni tanlaydi: **onlayn** (bir martalik) yoki **offlayn**
   (necha oyga). Frontend summani ko'rsatadi, lekin uni yubormaydi.
2. `POST /orders/` — backend summani o'zi hisoblaydi va `Order` yaratadi (`NEW`),
   javobda Click to'lov sahifasiga havola qaytadi.
3. Click ikki marta murojaat qiladi: **Prepare** (`action=0`) va **Complete** (`action=1`).
   Har ikkisida MD5 imzo va summa tekshiriladi.
4. Complete muvaffaqiyatli bo'lsa, `Enrollment` ochiladi: onlayn — muddatsiz, offlayn —
   to'langan oylar soniga `expires_at`. So'ng fiskal chek va xabar yuboriladi.

**Backend**

| # | Vazifa |
|---|---|
| 1 | `payments` app: `Order` (kim, qaysi kurs, shakl, necha oy, summa, holat), `PaymentTransaction` (`click_trans_id` unikal — idempotentlik shu yerda), `PaymentLog` (har bir so'rov va javob), `Refund` |
| 2 | Summa serverda: onlayn — `price_online`, offlayn — `price_offline_monthly × oy`. Bepul yoki allaqachon ochiq kursga buyurtma berilmaydi |
| 3 | `POST /orders/`, `GET /orders/`, `GET /orders/{id}/` (natija sahifasi holatni shu orqali kuzatadi) |
| 4 | Click callback'lari: `/payments/click/prepare/`, `/payments/click/complete/`. Autentifikatsiyasiz, CSRF'siz — himoya imzo orqali. Javob Click hujjatidagi xato kodlari bilan |
| 5 | Idempotentlik va poyga: `select_for_update` bilan tranzaksiya ichida; bir `click_trans_id` ikki marta qayta ishlanmaydi; takroriy to'lov `-4` bilan rad etiladi |
| 6 | Celery beat: 30 daqiqada to'lanmagan `NEW` buyurtma `EXPIRED` bo'ladi |
| 7 | Fiskal chek: `Course.mxik_code`, chek havolasi `PaymentTransaction`da. Click fiskalizatsiya API'si sozlanmaguncha dry-run (SMS'dagi kabi) |
| 8 | To'lovdan keyin SMS/Telegram xabari (chek havolasi bilan) |
| 9 | Admin: buyurtmalar (filtr: holat, kurs, sana), tranzaksiyalar va loglar faqat ko'rish uchun, refund yaratish va tasdiqlash. `Order` va `Refund` audit logga tushadi |
| 10 | Testlar: imzo (to'g'ri/noto'g'ri), summa mos emas, ikki marta Complete, Prepare'siz Complete, bekor qilingan tranzaksiya, muddati o'tgan buyurtma, offlayn oylarning `expires_at` ga ta'siri, kurs faqat Complete'dan keyin ochilishi |

**Frontend**

| # | Vazifa |
|---|---|
| 1 | Kurs sahifasida sotib olish paneli: shakl tanlash (onlayn / offlayn), offlayn uchun oylar soni, yakuniy summa |
| 2 | `POST /orders/` → Click sahifasiga o'tish. Kirmagan foydalanuvchi avval kirish sahifasiga yuboriladi |
| 3 | `/payment/result` — to'lov natijasi: holat backend'dan so'raladi (Click'dan qaytish isbot emas), muvaffaqiyatda kursga havola |
| 4 | Kabinetda "To'lovlarim": buyurtmalar tarixi, holati va chek havolasi |

**Chegaralar:** obuna, bundle, promo-kod, Payme va Uzum — 2-bosqich. Refund pulni avtomatik
qaytarmaydi: admin Click kabinetida qaytaradi va tizimda belgilaydi (TZ [B1] shunday).

**Tekshiruv:** pytest — Click'ning barcha holatlari; brauzerda dry-run to'lov bilan
kursning ochilishi.


### 7.8. 6-qadam: sifat va production — batafsil vazifalar

Maqsad: loyihani serverga chiqarishga tayyorlash va TZ 16-bo'limdagi 1-bosqich mezonlarini
avtomatik tekshiriladigan qilish.

**Xavfsizlik**

| # | Vazifa |
|---|---|
| 1 | **CSP nonce bilan** (`proxy.ts`): har so'rovda yangi nonce, `script-src 'self' 'nonce-…' 'strict-dynamic'`. Tashqi manbalar faqat keraklilari: Google va Telegram kirish oynalari, storage (video segmentlari va rasmlar), Sentry. Inline `style` atributlari uchun `style-src 'unsafe-inline'` (skriptlardan farqli ravishda xavfi past) |
| 2 | nginx (prod): TLS, HTTP → HTTPS, HSTS, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, `/_next/static` uchun uzoq kesh, auth endpointlariga IP bo'yicha limit |
| 3 | Django `prod.py`: `check --deploy` toza — xavfsiz cookie'lar, HSTS, `SECURE_PROXY_SSL_HEADER`, JSON loglar |

**Monitoring**

| # | Vazifa |
|---|---|
| 4 | Sentry: backend (Django + Celery) va frontend (`@sentry/nextjs`). DSN bo'lmasa o'chiq; shaxsiy ma'lumot yuborilmaydi (telefon raqamlari tozalanadi) |
| 5 | Biznes ogohlantirishlari Telegram'ga (`TELEGRAM_ALERTS_CHAT_ID`): to'lov callback xatolari, video qayta ishlash xatosi. Bir xil ogohlantirish 10 daqiqada bir martadan ko'p yuborilmaydi |
| 6 | Barcha servislarda `healthcheck` (`worker-video` va `beat` ham) |

**Backup (RPO ≤ 24 soat, 30 kun saqlanadi)**

| # | Vazifa |
|---|---|
| 7 | `backup` servisi: har kuni `pg_dump`, 30 kunlik rotatsiya, ixtiyoriy ravishda S3 bucket'ga nusxa. `restore.sh` va tiklash tartibi README'da |

**Production**

| # | Vazifa |
|---|---|
| 8 | `docker-compose.prod.yml`: runtime image'lar, `worker-video`, `backup`, TLS sertifikatlari, log hajmi cheklovi, DB porti tashqariga ochilmaydi |

**Testlar va CI**

| # | Vazifa |
|---|---|
| 9 | Frontend unit testlari (Vitest): narx, `safeNext`, vaqt formati kabi sof funksiyalar |
| 10 | E2E (Playwright): landing 3 tilda, katalog filtri, kirish → kabinet → dars, **to'lov** (Click callback'lari test kaliti bilan taqlid qilinadi) → kurs ochiladi. Test ma'lumotlari `seed_e2e` buyrug'i bilan tayyorlanadi |
| 11 | Accessibility (axe-core): asosiy sahifalarda `serious`/`critical` xato bo'lmasligi. CSP buzilishi ham testda xato hisoblanadi |
| 12 | CI (GitHub Actions): backend (ruff, mypy, pytest), frontend (eslint, tsc, vitest, build), E2E (butun stack Docker'da) |
| 13 | Lighthouse: production build'da landing va katalog o'lchanadi (Performance ≥ 85, SEO ≥ 95, Best Practices ≥ 95, Accessibility ≥ 90) |

**Chegaralar:** yuklama testi (k6), OWASP ZAP va mustaqil pentest — server tayyor bo'lgach,
staging'da. Deploy'ning o'zi (server, domen, sertifikat) buyurtmachi hosting tanlagandan keyin.

**Dev muhit:** Docker xotirasi cheklangan, shuning uchun E2E va Lighthouse **host'da** (o'rnatilgan
Chrome bilan) ishga tushiriladi, og'ir tekshiruvlar navbat bilan.


### 7.9. 6-qadam natijalari (2026-09-27)

**Lighthouse** (production build, shu kompyuterda — Lighthouse benchmark 867, ya'ni odatiy
o'lchov serverlaridan sekinroq; mobil = 4x CPU sekinlashtirish simulyatsiyasi):

| Sahifa | Desktop | Mobil | Accessibility | SEO | Best Practices |
|---|---|---|---|---|---|
| Landing `/uz` | **98** | 56–63 | 100 | 100 | 96 |
| Katalog `/uz/courses` | **100** | **86** | 98 | 100 | 100 |

Mobil landing'ning haqiqiy o'lchovi (Pixel 7 emulyatsiyasi): LCP elementi — hero sarlavhasi,
**0.25–0.86 s**. Simulyatsiyadagi past ball — og'ir gidratsiya (katta landing daraxti) va sekin host.
Qilingan: 3D telefonda faqat birinchi harakatdan keyin yuklanadi, desktopda — sahifa yuklanib
bo'shagach; bo'limlar alohida gidratsiya qilinadi (`<Suspense>`); brauzerga faqat kerakli
tarjimalar ketadi; hero sarlavhasi birinchi kadrdan ko'rinadi. **Yakuniy mobil o'lchov staging'da
PageSpeed Insights bilan qilinadi.** Keyingi qadam kerak bo'lsa: pastdagi interaktiv bloklarni
(kasb testi, ariza formasi) ko'ringanda yuklash.

**Topilgan va tuzatilgan xatolar:** proxy matcher faqat `/` da ishlardi (CSP va kabinet
himoyasi tilli sahifalarda ishlamasdi); kirishdan keyin `/uz/uz/...` bo'lib qolish; Docker
image'da `NEXT_PUBLIC_*` bo'sh qolishi (canonical URL, CSP storage, Sentry); Click'dan qaytish
manzilida til yo'qligi; kontrast (manifest so'zlari, dastur belgisi, dars davomiyligi) va
Google tugmasi atrofidagi ARIA.


## 7A. 2-bosqich: buyurtmachining yangi talablari (2026-09-27)

1-bosqich (0–6-qadamlar) tugagach buyurtmachi 13 ta talab berdi. Ularning ko'pi TZ'da [B2] edi;
tartib buyurtmachining ustuvorligi bo'yicha: eng katta muammo — ish vaqtidan keyin kelgan
mijozlar javobsiz qolishi (AI agent).

| Qadam | Nima | Talab |
|---|---|---|
| **7** ✅ | Kabinet: barcha kurslar kabinet ichida (menyu bilan), **SIFAT Kids kabineti** (alohida, kreativ), loader, **dars materiallari va darsdagi kodlar**, premium kurs sahifasi | 0, 5, 8, 12, 13 |
| **8** ✅ | **AI sotuv agenti 24/7**: saytdagi chat (kasb testi yonida va har sahifada), keyin Telegram bot. Kurslar va narxlar bazadan olinadi, ariza yaratadi, kerak bo'lsa menejerga uzatadi | 2, 4 |
| **9** ✅ | **Rollar**: o'quvchi, o'qituvchi, menejer, admin, direktor — har biriga o'z ruxsatlari va paneli; o'qituvchi guruhlari | 3 |
| **10** ✅ | **Admin statistikasi va xabarnomalar**: bugun nechta ro'yxatdan o'tdi, nechtasi kurs tanladi yoki to'ladi, qanday xatolar bo'ldi; Telegram va SMS orqali xabar yuborish | 11 |
| **11** ✅ | **Uy vazifalari**: fayl, kod yoki rasm yuklash; o'qituvchi tekshiradi, baho va izoh beradi | 1 |
| **12** ✅ | **Testlar va o'yinlar**: dars/modul testlari, o'yinli mashqlar (tushunganini tekshirish) | 7 |
| **13** | **Jonli darslar**: o'qituvchi haftasiga 1–2 marta Meet o'tkazadi — jadval, eslatma, yozuv | 6 |
| **14** | **XP, musobaqalar va magazin**: XP yig'ish, reyting, musobaqalar, XP ga narsa olish — **7B-bo'limda qayta rejalandi** (bot, testlar, XP va referal bilan: 13–18-qadamlar) | 9, 10 |

**Qabul qilingan yechimlar (o'zgartirish mumkin):**

* **AI:** Claude API (Anthropic). Agent javobni o'ylab topmaydi: kurs, narx va jadvalni
  **bazadan vosita (tool) orqali** oladi. Ariza qoldirish ham vosita — ariza admin va Telegram'ga
  tushadi. Kunlik budjet va suhbat uzunligi cheklanadi. API kaliti kerak.
* **Meet:** o'qituvchi Google Meet/Zoom havolasini jadvalga qo'yadi (Google API kerak emas);
  eslatma Telegram yoki SMS orqali.
* **Rollar:** Django guruhlari va ruxsatlari. Direktor — hamma hisobot, faqat o'qish;
  menejer — arizalar, o'quvchilar, to'lovlar; o'qituvchi — o'z guruhlari, uy vazifalari, meet;
  admin — hammasi.
* **XP:** har bir harakat uchun yozuv (`XPTransaction`) — balans hisoblanadi, tarix ko'rinadi.
  Magazindagi narsalarni admin qo'shadi (raqamli yoki jismoniy, zaxira bilan).
* **Xabarnoma:** Telegram orqali yozish uchun foydalanuvchi ruxsat berishi kerak — Telegram
  kirish vidjeti "xabar yuborishga ruxsat" so'raydi; telefon bilan kirganlar sozlamalarda
  Telegram'ni ulaydi. Qolganlarga SMS (pullik).

### 7A.1. 7-qadam natijalari (2026-09-27)

| Talab | Nima qilindi |
|---|---|
| 0 — kurslar kabinetdan chiqib ketardi | `/dashboard/catalog` va `/dashboard/catalog/{slug}`: katalog va kurs sahifasi kabinet ichida, menyuda "Barcha kurslar". Sayt va kabinet bitta komponentdan foydalanadi (`CatalogView`, `CourseDetailView`) |
| 5 — SIFAT Kids kabineti | To'liq qayta chizildi: robot-maskot, "Bugungi sarguzasht" (keyingi dars), darslar xaritasi (modul — orol, dars — tosh: tugatilgan, hozirgi, yopiq), yulduzlar va 4 ta medal. Sozlamalarda yoqiladi |
| 8 — materiallar va kodlar | `LessonMaterial` (fayl / havola / kod), admin'da dars ichida. Fayl — yopiq bucket, faqat huquqi bor o'quvchiga imzolangan havola; kod — nusxalash va yuklab olish |
| 12 — premium | To'langan kurs: oltin belgi, progress halqasi, darslar, soat, muddat yoki "umrbod"; kartochkada ham belgi. O'quvchi sotib olgan shakl ko'rsatiladi (oldin kursning umumiy shakli chiqardi — tuzatildi) |
| 13 — loader | Kabinetda `loading.tsx` (brend loaderi); sayt va kirish sahifalarida yuqorida chiziq. Saytda `loading.tsx` qo'yilganda 404 sahifalar 200 qaytardi (streaming) — E2E ushladi, shuning uchun chiziqqa almashtirildi |
| Qo'shimcha | Kabinet uchun o'z 404 sahifasi (menyu bilan, 3 tilda); topilmagan kurs/dars sarlavhasi "Sahifa topilmadi"; kabinetdagi sanalar tanlangan tilda |

Tekshiruv: backend 282 test, ruff, mypy; frontend typecheck, eslint, 39 Vitest; **20 ta E2E**
(yangi: kabinet katalogi, kabinet 404, SIFAT Kids ko'rinishi, premium, haqiqiy 404) — hammasi o'tdi.


### 7A.2. 8-qadam: AI sotuv maslahatchisi (24/7) — batafsil vazifalar

Maqsad: ish vaqtidan keyin yozgan mijoz javobsiz qolmasin. AI savollarga javob beradi, mos kursni
tanlashga yordam beradi, raqamini olib menejerlarga ariza qoldiradi.

**Qanday ishlaydi**

1. Mijoz saytda (kasb testi yonida yoki istalgan sahifadagi tugma orqali) yoki Telegram botda yozadi.
2. Xabar navbatga tushadi (Celery, alohida `ai` navbati). Worker uni Claude'ga yuboradi; javob
   bo'lak-bo'lak Redis'ga yoziladi, sayt uni har ~0,7 soniyada olib turadi — matn yozilayotgandek chiqadi.
3. Agent faktlarni **bazadan** oladi: kurslar va narxlar, ish vaqti, manzil, FAQ, "xavotirlar",
   "qanday o'qiymiz" va admin yozgan qo'shimcha ma'lumot. Bazada yo'q narsani o'ylab topmaydi —
   "menejer aniqlab beradi" deydi va raqam so'raydi.
4. Mijoz raqamini yozsa, agent ariza yaratadi (`Lead`, manba — AI chat): ariza admin va Telegram
   guruhiga tushadi. Shikoyat yoki javobi yo'q savolda suhbat "Menejer kerak" holatiga o'tadi.

**Qarorlar**

* **Model:** standart — Claude Opus 5 (1M token uchun: kiruvchi $5, chiquvchi $25, keshdan o'qish
  $0,50), fikrlash chuqurligi `low`. `.env`da `ASSISTANT_MODEL` bilan almashtiriladi: Sonnet 5
  ($2 / $10) yoki Haiku 4.5 ($1 / $5) — tanlov buyurtmachida. Taxminan: 10 xabarli suhbat Opus 5
  bilan ≈ $0,08–0,15, Sonnet 5 bilan ≈ $0,03–0,06. Opus 5'da xavfsizlik klassifikatori so'rovni
  rad etsa, API uni server tomonda boshqa modelda qayta bajaradi (`fallbacks: "default"`).
* **Claude API qoidalari:** joriy modellar standart holatda fikrlaydi — `thinking` bloklari tarixda
  o'zgarishsiz qaytariladi (vosita siklida shart), `max_tokens` 16000 (fikrlash ham shunga kiradi);
  vosita kiritmasi streaming bilan keladi va har bir vosita uni o'zi tekshiradi; `refusal` yoki
  bo'sh javobda mijozga zaxira javob beriladi.
* **Prompt caching:** tizim prompti (kurslar, FAQ) barcha suhbatlar uchun, tarix esa suhbat ichida keshlanadi.
* **Telefon raqamlari AI'ga yuborilmaydi** (TZ 4.9): matndagi raqam `‹telefon-1›` belgisiga
  almashtiriladi, ariza yaratilganda backend haqiqiy raqamni qo'yadi. AI raqamni o'ylab topa olmaydi.
* **Oflayn rejim** (kalit yo'q, budjet tugagan yoki API xatosi): qoidaga asoslangan javob — kurslar
  ro'yxati va raqam so'rash; raqam yozilsa ariza baribir yaratiladi. Local'da `ASSISTANT_DRY_RUN=true`
  shu rejimni "test rejimi" belgisi bilan ko'rsatadi.
* **Cheklovlar:** kunlik va oylik budjet (admin'da, standart $5 va $100), suhbatda 30 ta xabar,
  IP bo'yicha soatiga 60 ta, xabar 1000 belgigacha. Oylik budjetning 80 foizida Telegram ogohlantirish.
* **Saqlash:** suhbatlar 90 kun, keyin matn va shaxsiy ma'lumot o'chiriladi (statistika qoladi).
* **Nega SSE emas, navbat:** Telegram'ga ham shu yo'l kerak; web jarayonlari uzoq band bo'lmaydi;
  SMS kodlari alohida navbatda qoladi.
* **Telegram:** o'sha bot. Production'da webhook (`secret_token` bilan), local sinov uchun polling
  buyrug'i. Guruh xabarlari e'tiborsiz qoldiriladi; "Raqamni yuborish" tugmasi bor.

**Backend**

| # | Vazifa |
|---|---|
| 1 | `assistant` app: `AssistantSettings` (yoqilgan, qo'shimcha ma'lumot, kunlik/oylik budjet, xabar limiti), `Conversation` (kanal, holat, foydalanuvchi, Telegram chat, ariza, sahifa, kontekst, xarajat), `Message` (rol, matn, API bloklari, kurs kartochkalari, tokenlar, narx, 👍/👎) |
| 2 | `Lead.source`: sayt formasi / AI sayt / AI Telegram — 10-qadam statistikasi uchun |
| 3 | Tizim prompti bazadan, suhbat tilida: qoidalar, kurslar va narxlar, FAQ, xavotirlar, "qanday o'qiymiz", aloqa, ish vaqti, admin yozgan ma'lumot |
| 4 | Vositalar: `get_course` (dastur, ustozlar, narxlar), `show_courses` (chatda kurs kartochkalari), `create_lead` (ariza; mavzu: yozilish / savol / shikoyat / o'quvchi muammosi) |
| 5 | Agent sikli: streaming, bitta javobda 4 tagacha vosita, token va xarajat hisobi, budjet tugasa yoki API xato bersa — oflayn rejim va ogohlantirish |
| 6 | API: `GET/POST/DELETE /assistant/chat/` (suhbat HttpOnly cookie orqali, CSRF bilan), `POST /assistant/chat/rate/`; sayt sozlamalarida `assistant_enabled` |
| 7 | Telegram: webhook, `/start`, kontakt, matn; `telegram_webhook` va `telegram_poll` buyruqlari |
| 8 | `worker-ai` servisi (`ai` navbati, threads, 8 ta parallel javob); beat: 90 kunlik tozalash |
| 9 | Admin, "AI yordamchi" bo'limi: suhbatlar (transkript, holat, filtrlar, ariza havolasi, xarajat), sozlamalar (bugungi va oylik xarajat); arizalarda manba |
| 10 | Sifat: `assistant_eval` buyrug'i — 3 tilda ssenariylar (narxlar to'g'riligi, javob tili, raqam so'rash, mavzudan chiqmaslik). API kaliti kelganda ishga tushiriladi |
| 11 | Testlar: soxta model bilan agent sikli, vositalar, raqam belgilari, budjet, API, Telegram, tozalash |

**Frontend**

| # | Vazifa |
|---|---|
| 1 | Chat paneli: xabarlar, yozilayotgan matn, tezkor savollar, kurs kartochkalari, 👍/👎, "Yangi suhbat", maxfiylik eslatmasi |
| 2 | Kasb testi yonida (o'ngda) ochiq chat; test natijasi chatga kontekst bo'lib o'tadi ("natijam bo'yicha maslahat") |
| 3 | Boshqa sahifalarda pastki o'ng burchakda tugma; telefonda chat to'liq ekranda ochiladi |
| 4 | Accessibility: `role="log"`, klaviatura, fokus, reduced motion; 3 til |
| 5 | Testlar: Vitest (xabar matni renderi), E2E (test rejimida suhbat va ariza, axe) |

**Chegaralar (keyinroq):** menejerning chatga jonli qo'shilishi (hozircha menejer telefon orqali
bog'lanadi), ovozli xabar va rasm, kabinetdagi support chat, darslar bo'yicha AI (TZ 4.9).

**Tekshiruv:** pytest (agent, vositalar, API, Telegram); E2E test rejimida. API kaliti kelganda —
`assistant_eval` va brauzerda haqiqiy suhbat.


### 7A.3. 8-qadam natijalari (2026-09-28)

| Qism | Holat |
|---|---|
| Saytdagi chat | Kasb testi yonida (o'ngda) ochiq chat va boshqa sahifalarda suzuvchi tugma (telefonda to'liq ekran). Javob yozilayotgandek chiqadi; kurs kartochkalari, 👍/👎, "Yangi suhbat". Kasb testi natijasi chatga kontekst bo'lib o'tadi |
| Agent | Kurslar, narxlar, FAQ, xavotirlar, aloqa va admin yozgan ma'lumot bazadan; vositalar: `get_course`, `show_courses`, `create_lead`. Ariza manbasi — "AI chat"; shikoyat va o'quvchi muammosida suhbat "Menejer kerak" |
| Xavfsizlik | Telefon raqamlari AI'ga belgi bilan boradi, karta raqamlari saqlanmaydi, AI raqam o'ylab topa olmaydi; CSRF, cookie xeshi, IP limiti; 90 kunlik anonimlashtirish |
| Claude API | Standart model — Claude Opus 5 (`effort: low`, rad etilsa server tomonda boshqa modelga o'tadi). `thinking` bloklari tarixda saqlanadi, `max_tokens` 16000, bo'sh yoki rad etilgan javobda zaxira javob. Kalit bo'lmasa, budjet tugasa yoki API xato bersa — oddiy rejim raqam so'raydi |
| Telegram | Webhook (maxfiy kalit bilan) va local polling buyrug'i; `/start`, "Raqamni yuborish" tugmasi (faqat o'z raqami), guruhlar e'tiborsiz |
| Admin | "AI yordamchi": suhbatlar (transkript, vositalar, 👎 filtri, "Menejer kerak" soni menyuda), sozlamalar (budjet, qo'shimcha ma'lumot, bugungi va oylik xarajat); arizalarda manba va suhbatga havola |
| Qo'shimcha | Katalog sahifasida kurs kartochkalari va sarlavha uslubsiz qolgan edi (7-qadamda CSS importi tushib qolgan) — uslublar komponentlarning o'ziga ko'chirildi |

Tekshiruv: backend 356 test, ruff, mypy, OpenAPI; frontend typecheck, eslint, 44 Vitest; **22 ta E2E**
(yangi: kasb testi yonidagi chat — kurslar va ariza, suzuvchi oyna va klaviatura, axe) — hammasi o'tdi.
Test rejimida (`ASSISTANT_DRY_RUN=true`) butun yo'l ishlaydi: sayt → navbat → `worker-ai` → javob.

**Kutilmoqda:** Anthropic API kaliti (va model tanlovi), Telegram bot token + domen (webhook uchun).
Kalit kelgach: `assistant_eval` va brauzerda haqiqiy suhbat.


### 7A.4. 9-qadam: rollar — batafsil vazifalar

Maqsad: har bir xodim o'z ishini ko'radi va boshqasiga tegmaydi. Rollar — Django guruhlari; kim
nima qila olishi kodda bitta jadvalda turadi va `migrate`dan keyin avtomatik sinxronlanadi.

| Rol | Kim | Qayerda ishlaydi | Nima qila oladi |
|---|---|---|---|
| O'quvchi | Ro'yxatdan o'tgan har kim | Kabinet | O'z kurslari, to'lovlari va sozlamalari |
| O'qituvchi | Ustoz | Kabinet → "Guruhlarim"; admin → o'z kurslari | O'z guruhlari va o'quvchilarining progressi. O'z kurslariga modul, dars, material va video qo'shadi (narx va nashr — yo'q) |
| Menejer | Sotuv va o'quv bo'limi | Admin | Arizalar, AI suhbatlar, o'quvchi akkaunti, kursga yozish, guruhlar. Buyurtmalarni ko'radi, pul qaytarish so'rovini ochadi |
| Direktor | Rahbar | Admin | Hamma narsani ko'radi, o'zgartirmaydi; 10-qadamda — kunlik statistika |
| Admin | Tizim egasi | Admin | Hammasi: sayt kontenti, narxlar, AI sozlamalari, rol berish, pul qaytarishni tasdiqlash |

Bir odamda bir nechta rol bo'lishi mumkin (masalan, o'qituvchi va menejer). TZ'dagi "Support
operator" olib tashlandi: murojaatlar va AI suhbatlar menejerda.

**Backend**

| # | Vazifa |
|---|---|
| 1 | `Role`: STUDENT, TEACHER, MANAGER, DIRECTOR, ADMIN. Ruxsatlar jadvali kodda; `migrate`dan keyin guruhlar va ruxsatlar avtomatik sinxronlanadi, `sync_roles` buyrug'i ham bor |
| 2 | `StudyGroup` (guruh): kurs, o'qituvchi, nomi, shakl, jadval, boshlanish sanasi, holat, sig'im. `Enrollment.group` — o'quvchi guruhga biriktiriladi (kurs mosligi tekshiriladi) |
| 3 | Admin'da foydalanuvchi sahifasida "Rollar" (faqat Admin o'zgartiradi); rol admin'ga kirishni (`is_staff`) o'zi beradi va oladi. `grant_role` buyrug'i |
| 4 | Guruh sahifasi (admin): o'quvchilarni kursga yozilganlar ichidan tanlash, a'zolar ro'yxati progress bilan |
| 5 | O'qituvchi admin'da faqat o'z kurslarini (kursga ustoz sifatida biriktirilgan) ko'radi: modul, dars, material, video. Menyuda faqat ruxsati bor bo'limlar chiqadi |
| 6 | API: `GET /teacher/groups/`, `GET /teacher/groups/{id}/` — faqat o'z guruhlari: o'quvchilar, progress, oxirgi faollik. `me` javobida `roles` |
| 7 | Testlar: har rol uchun admin sahifalari (200 / 403), o'qituvchi faqat o'zinikini ko'radi, rol `is_staff`ni boshqaradi, guruh va kurs mosligi |

**Frontend**

| # | Vazifa |
|---|---|
| 1 | Kabinet menyusi rolga qarab: o'qituvchiga "Guruhlarim", xodimlarga "Boshqaruv paneli" (admin) havolasi |
| 2 | "Guruhlarim": guruh kartochkalari (kurs, shakl, jadval, o'quvchilar soni, o'rtacha progress) va guruh sahifasi — o'quvchilar ro'yxati (ism, telefon, progress, oxirgi faollik; orqada qolganlar tepada) |
| 3 | E2E: o'qituvchi kiradi, guruhini va o'quvchisini ko'radi; axe |

**Chegaralar:** uy vazifalari (11-qadam) va jonli darslar (13-qadam) o'qituvchi sahifasiga keyin
qo'shiladi; direktor statistikasi — 10-qadam; xodimlar uchun ikki bosqichli kirish (2FA) — keyinroq.

**Tekshiruv:** pytest (ruxsatlar matritsasi), E2E (o'qituvchi kabineti).


### 7A.5. 9-qadam natijalari (2026-09-28)

| Qism | Holat |
|---|---|
| Rollar | O'quvchi, O'qituvchi, Menejer, Direktor, Admin — Django guruhlari; ruxsatlar jadvali kodda, `migrate`dan keyin o'zi sinxronlanadi (`sync_roles`). Rol `is_staff`ni o'zi boshqaradi. `grant_role` buyrug'i |
| Admin | Foydalanuvchi sahifasida "Rollar" (faqat Admin); Menejer o'quvchi akkauntini o'zgartiradi, xodimlarnikini — yo'q; superuser belgisi faqat superuser'ga. Menyuda faqat ruxsati bor bo'limlar. O'qituvchi faqat o'z kurslarining modul, dars, material va videolarini ko'radi va tanlov maydonlari ham cheklangan. Video yuklash — faqat yuklash huquqi bor rolga |
| Guruhlar | `StudyGroup` (kurs, o'qituvchi, shakl, jadval, holat, sig'im); o'quvchilar kursga yozilganlar ichidan tanlanadi, guruh boshqa kursniki bo'lsa rad etiladi |
| O'qituvchi kabineti | "Guruhlarim": guruh kartochkalari (o'rtacha progress) va guruh sahifasi — o'quvchilar, progress, oxirgi faollik, "7 kundan beri kirmagan" va "to'lov muddati o'tgan" belgilari; orqada qolganlar tepada. Telefonda qatorlar kartochka bo'ladi |
| Kabinet menyusi | Rolga qarab: o'qituvchiga "Guruhlarim", xodimlarga "Boshqaruv paneli" |

Tekshiruv: backend 390 test (ruxsatlar matritsasi, o'qituvchi faqat o'zinikini ko'radi, rol
berish), ruff, mypy, OpenAPI; frontend 47 Vitest; **24 ta E2E** (yangi: o'qituvchi kabineti va
o'quvchi bu bo'limni ko'rmasligi, axe) — hammasi o'tdi.

**AI maslahatchi:** Anthropic kaliti ulandi va tekshirildi, lekin hisobda kredit yo'q — Claude
javob bermaguncha oddiy rejim ishlaydi. Telegram bot tokeni ulandi (@sifatedu_managerbot);
webhook domen kelganda o'rnatiladi.

### 7A.6. 10-qadam: kunlik statistika va xabarnomalar — batafsil vazifalar

Maqsad: admin, direktor va menejer bir qarashda bugun nima bo'lganini ko'radi — kim ro'yxatdan
o'tdi, kim kurs tanladi yoki to'ladi, qayerda muammo bor. Ro'yxatdan o'tganlarga admin paneldan
xabar yuboriladi: kabinetga, Telegram'ga, kerak bo'lsa SMS orqali.

**1. Kunlik statistika — admin bosh sahifasi (`/admin/`)**

Davr: bugun, kecha, 7 kun yoki 30 kun (Toshkent vaqti). Admin, Direktor va Menejer ko'radi,
O'qituvchi ko'rmaydi.

| Blok | Nima ko'rsatadi |
|---|---|
| Asosiy raqamlar | Ro'yxatdan o'tganlar (shundan Kids va Telegram orqali), kurs tanlaganlar (kursga yozilgan yoki to'lovni boshlagan), to'laganlar (soni va summasi), arizalar (sayt / AI), AI suhbatlar va xarajati. Har biri oldingi davr bilan solishtiriladi |
| Voronka | Ro'yxatdan o'tdi → kursga yozildi → to'lovni boshladi → to'ladi (foizlarda) |
| 30 kunlik grafik | Har kungi ro'yxatdan o'tishlar va to'lovlar |
| Muammolar | Faqat bor bo'lsa, havolasi bilan: 2 soatdan beri javobsiz arizalar; menejer kutayotgan AI suhbatlar; AI javob bera olmagan yoki Claude'siz ishlagan holatlar; kiritilmagan SMS kodlari (SMS yetib bormayotgan bo'lishi mumkin); yakunlanmagan to'lovlar va to'lov xatolari; pul qaytarish so'rovlari; video xatolari; yetkazilmagan xabarlar; tizim xatolari bo'limlar bo'yicha (server, to'lov, SMS/Telegram, AI, video) |
| Qo'ng'iroq qilish kerak | Davr ichida ro'yxatdan o'tib, kurs tanlamaganlar (ism, telefon, vaqt) va offlayn to'lov muddati tugaganlar (7 kun ichida). To'liq ro'yxat — foydalanuvchilar va kursga yozilishlar sahifasida, filtr bilan |

* **Tizim xatolari:** har bir `ERROR` log yozuvi Redis'da kun va bo'lim bo'yicha sanaladi
  (40 kun saqlanadi). Tafsilot — Sentry'da.
* **Telegram hisobot:** har kuni 21:00 da direktor va adminlarga (Telegram'i ulangan bo'lsa) —
  bugungi raqamlar, muammolar va admin panelga havola. Istalsa, guruhga ham (`TELEGRAM_REPORTS_CHAT_ID`).

**2. Xabarnomalar**

| Kanal | Kimga boradi | Narxi |
|---|---|---|
| Kabinet — menyuda 🔔 "Xabarlar" | Hammaga | Bepul |
| Telegram (@sifatedu_managerbot) | Telegram'ini ulaganlarga | Bepul |
| SMS (Eskiz) | Telegram'i yo'qlarga, admin tanlasa | Pullik; matn Eskiz'da tasdiqlangan shablonga mos bo'lishi shart |

**Telegram qanday ulanadi**

* Telegram orqali ro'yxatdan o'tganlar — avtomatik: kirish oynasi "xabar yuborishga ruxsat"
  so'raydi (production'da, domen bilan).
* Telefon bilan ro'yxatdan o'tganlar — kabinet → Sozlamalar → **"Telegram'ni ulash"**: tugma
  botni ochadi, "Start" bosiladi — tayyor. Havola bir martalik, 10 daqiqa amal qiladi. Bot
  "ulandi" deb javob beradi, sahifa o'zi yangilanadi. Kabinet bosh sahifasida ulanmaganlarga eslatma turadi.
* Foydalanuvchi botni bloklasa, tizim buni Telegram javobidan biladi va unga Telegram orqali
  yubormaydi. Botga qayta yozsa — yana yuboriladi.

**Admin'dan xabar yuborish** (admin → Xabarnomalar → Xabar yuborish)

* **Kimga:** hamma, kattalar yoki SIFAT Kids; tanlangan kurslar yoki guruhlar o'quvchilari; faqat
  kurs tanlamaganlar; ro'yxatdan o'tgan sana oralig'i.
* **Turi:** "O'quv xabari" (dars, jadval, to'lov) — hammaga. "Aksiya va yangilik" — kabinetga
  hammaga, Telegram va SMS orqali esa faqat rozilik berganlarga (TZ 4.12, reklama qonuni). Kechasi
  (22:00–09:00) yuborilmaydi, 09:00 ga suriladi.
* **Matn:** sarlavha, matn, ixtiyoriy havola (Meet, kurs sahifasi), SMS uchun alohida qisqa matn.
* **Yuborishdan oldin** tasdiqlash sahifasi: necha kishiga, shundan Telegram, SMS va faqat kabinet;
  SMS'ning taxminiy narxi. "Menga sinov uchun yuborish" tugmasi bor.
* **Natija:** har kanal bo'yicha yuborildi, xato va navbatda; kabinetda nechtasi o'qidi.
* **Ruxsat:** Admin va Menejer yuboradi, Direktor faqat ko'radi.

**Avtomatik xabarlar** (foydalanuvchi tilida, har biri bir marta)

| Hodisa | Qachon | Kanal |
|---|---|---|
| To'lov qabul qilindi (chek havolasi bilan) | To'lovdan keyin | Kabinet va Telegram; Telegram bo'lmasa — SMS (hozirgidek) |
| Kurs ochildi | Admin kursni qo'lda ochganda | Kabinet va Telegram |
| Offlayn to'lov muddati tugayapti | 3 kun qolganda, soat 10:00 da | Kabinet va Telegram |
| Offlayn to'lov muddati tugadi | Tugagan kuni, soat 10:00 da | Kabinet va Telegram |

**Rozilik:** ro'yxatdan o'tish formasida "Aksiya va yangiliklarni olishga roziman" katakchasi
(oldindan belgilanmagan) va sozlamalarda. Telegram xabarlarini sozlamalarda o'chirish mumkin.

**Backend**

| # | Vazifa |
|---|---|
| 1 | `notifications`: `Notification` (foydalanuvchi, tur, sarlavha, matn, havola, o'qilgan vaqti; har kanal holati va xatosi; takrorlanmaslik kaliti) va `Broadcast` (matn, auditoriya filtrlari, tur, kanallar, holat, muallif, yuborilgan vaqti) |
| 2 | `notify()` — yagona kirish nuqtasi: kabinetga yozadi va kanallarni navbatga qo'yadi. Ommaviy yuborish alohida `bulk` navbatida: 25 talik to'plamlar, soniyasiga ~25 xabar (Telegram limiti — 30), 429 javobida kutib qayta uriniladi. SMS kodlari `default` navbatida qoladi va kutib qolmaydi |
| 3 | Telegram ulash: bir martalik token (Redis, 10 daqiqa, xeshlangan), botda `/start c_<token>`, bloklash va qaytish (`my_chat_member`). `SocialAccount`ga `notify` va `blocked_at` maydonlari. Bot nomi `getMe` orqali olinadi — `TELEGRAM_BOT_USERNAME` shart emas |
| 4 | API: `GET /notifications/`, `POST /notifications/read/`, `me.unread_notifications`, `GET/PATCH /me/notifications/` (Telegram holati, Telegram xabarlari, rozilik), `POST /me/telegram/connect/`; ro'yxatdan o'tishda `marketing_consent` |
| 5 | Admin, "Xabarnomalar" bo'limi: xabar yuborish (tasdiqlash sahifasi, sinov yuborish, natijalar) va yuborilgan xabarlar (faqat ko'rish). Foydalanuvchilar ro'yxatida "Kurs tanlamagan" va "Telegram ulangan" filtrlari |
| 6 | Avtomatik xabarlar: to'lov (hozirgi SMS o'rniga `notify()`), qo'lda ochilgan kurs, muddat eslatmalari (beat, 10:00) |
| 7 | `stats` app: hisob-kitob (davrlar, voronka, 30 kunlik qator, muammolar), xato hisoblagichi (logging handler → Redis), `view_statistics` ruxsati (Admin, Direktor, Menejer), Unfold bosh sahifasi (kartochkalar, grafik, muammolar, qo'ng'iroq ro'yxati), 21:00 dagi Telegram hisobot |
| 8 | Testlar: Toshkent vaqti bo'yicha kun chegaralari, muammolar, auditoriya filtrlari va rozilik, yuborish (Telegram xatosi, bloklash, 429), bir martalik token, ruxsatlar, avtomatik xabarlar takrorlanmasligi |

**Frontend**

| # | Vazifa |
|---|---|
| 1 | Kabinet menyusida "Xabarlar" 🔔 va o'qilmaganlar soni (kattalar va Kids kabinetida) |
| 2 | "Xabarlar" sahifasi: yangilari ajralib turadi, havola tugmasi, ochilganda o'qilgan bo'ladi; bo'sh holatda Telegram'ni ulash taklifi |
| 3 | Sozlamalar → "Xabarnomalar": Telegram holati va "Telegram'ni ulash" (ulanishni kutib, o'zi yangilanadi), Telegram xabarlarini yoqish/o'chirish, aksiyalar roziligi |
| 4 | Kabinet bosh sahifasi: Telegram ulanmagan bo'lsa — kichik eslatma |
| 5 | Ro'yxatdan o'tish formalarida rozilik katakchasi |
| 6 | E2E: xabar ko'rinadi va o'qilgan bo'ladi, sozlamalar, axe |

**Chegaralar (keyinroq):** o'qituvchi o'z guruhiga xabar yuborishi va Meet eslatmalari — 13-qadam;
"uy vazifasi baholandi" — 11-qadam; faolsizlik eslatmalari (3 va 7 kun) va streak — 12/14-qadam;
xabarni belgilangan vaqtga rejalashtirish; email va web push; chuqur analitika (kogortalar,
retention — TZ 4.19.1, 3-bosqich).

**Tekshiruv:** pytest; E2E; admin bosh sahifasi va xabarnoma sahifalarining skrinshotlari.


### 7A.7. 10-qadam natijalari (2026-09-29)

| Qism | Holat |
|---|---|
| Kunlik statistika | Admin bosh sahifasi: bugun / kecha / 7 / 30 kun (Toshkent vaqti). Beshta asosiy raqam oldingi davr bilan, voronka, 30 kunlik grafik, muammolar (faqat borlari, havola ruxsatga qarab beriladi), qo'ng'iroq ro'yxatlari. Admin, Direktor va Menejer ko'radi, O'qituvchiga odatiy sahifa ochiladi |
| Tizim xatolari | Har bir `ERROR` log (server, to'lov, SMS/Telegram, kirish, AI, video, fon vazifalari) Redis'da kun va bo'lim bo'yicha sanaladi — Celery worker'larida ham. Sinovda o'zi ishladi: kod tahriri paytidagi worker xatolarini ko'rsatdi |
| Kunlik hisobot | 21:00 da direktor va adminlarga Telegram'da (Telegram'i ulangan bo'lsa) va ixtiyoriy guruhga; bot bloklangan bo'lsa, bu belgilanadi |
| Xabarnomalar | `Notification` (kabinet va Telegram/SMS holati) va `Broadcast`. Yagona `notify()`; ommaviy yuborish `bulk` navbatida: 25 talik to'plam, soniyasiga bitta, 429 javobida kutib qayta urinish, tarmoq xatosida 5 marta. SMS — faqat Telegram yetmasa |
| Admin'da xabar yuborish | Filtrlar (kabinet turi, kurslar, guruhlar, kurs tanlamaganlar, sana), kanallar, tasdiqlash oynasi (necha kishiga, qaysi kanal orqali, SMS narxi), "Menga sinov", natija. Yuborilgan xabar o'zgarmaydi va o'chirilmaydi. Admin va Menejer yuboradi, Direktor ko'radi |
| Telegram'ni ulash | Kabinet sozlamalarida bir martalik havola (10 daqiqa, soatiga 10 ta) → botda "Start". Botni bloklash va qaytishni bot o'zi biladi. Telegram orqali kirganlar avtomatik ulangan |
| Avtomatik xabarlar | To'lov qabul qilindi (oldin faqat SMS edi), qo'lda ochilgan kurs, offlayn to'lov muddati: 3 kun qolganda va tugaganda. Har biri bir marta yuboriladi |
| Rozilik | Ro'yxatdan o'tishning ikkala formasida va sozlamalarda. Aksiya Telegram va SMS orqali faqat rozilik berganlarga boradi, kechasi yuborilsa 09:00 ga suriladi |
| Kabinet | "Xabarlar" sahifasi, menyuda o'qilmaganlar soni, yuqori panelda qo'ng'iroqcha; bosh sahifada va "Xabarlar"da Telegram taklifi. Sanalar serverda Toshkent vaqtida formatlanadi (Chrome'da o'zbekcha oy nomlari yo'q) |

Tekshiruv: backend 451 test, ruff, mypy, OpenAPI; frontend typecheck, eslint, 49 Vitest;
**26 ta E2E** (yangi: xabarlar va menyudagi son, aksiyalar roziligi; axe). Admin statistikasi,
tasdiqlash oynasi va kabinet sahifalari yorug', tungi va telefon ko'rinishida skrinshot bilan tekshirildi.
Sinovda topilib tuzatildi: kichik matnlarda kontrast, Chrome'dagi sana formati, Telegram havolasi limiti.


### 7A.8. 11-qadam: uy vazifalari — batafsil vazifalar

Maqsad: o'qituvchi darsga uy vazifasi beradi, o'quvchi javobini fayl, kod, rasm yoki havola
bilan yuboradi, o'qituvchi platformadan chiqmasdan tekshirib baho va izoh qo'yadi. O'quvchi
kerak bo'lsa qayta ishlab yuboradi.

**Qanday ishlaydi**

1. O'qituvchi admin'da darsga **uy vazifasi** qo'shadi (dars sahifasidagi blok): topshiriq matni
   va ixtiyoriy muddat. Har bir darsda bitta vazifa.
2. O'quvchi dars sahifasida vazifani ko'radi va javob yuboradi. Javobda istalgan birikma bo'lishi
   mumkin: izoh, kod (til tanlanadi), havola (GitHub, sayt, Scratch) va fayllar — rasm, arxiv,
   hujjat (5 tagacha, har biri 20 MB gacha). Yuklash jarayoni foizda ko'rinadi.
3. Javob o'qituvchiga boradi: **guruh ustoziga**, guruhi bo'lmasa — **kurs ustozlariga**.
   Ularga kabinetda va Telegram'da xabar keladi, menyuda "Tekshirish" soni ko'rinadi.
4. O'qituvchi javobni kabinetda ochadi: kod, rasm va fayllar shu yerda, oldingi urinishlar va
   izohlar ham. Ikki qaror: **"Qabul qilish"** (baho 0–100 va izoh) yoki **"Qayta ishlashga
   qaytarish"** (izoh majburiy).
5. O'quvchiga natija keladi (kabinet va Telegram). Qaytarilgan bo'lsa, yangi urinish yuboradi —
   oldingilari tarixda qoladi. Tekshirilmagan javobni o'quvchi qaytarib olib, qayta yuborishi mumkin.

| Holat | Ma'nosi |
|---|---|
| Topshirilmagan | Hali javob yo'q |
| Tekshirilmoqda | Javob yuborilgan, o'qituvchi ko'rmagan |
| Qayta ishlash kerak | O'qituvchi izoh bilan qaytargan |
| Qabul qilindi | Baho qo'yilgan (0–100) |

**Qarorlar**

* **Baho 0–100.** 14-qadamdagi XP va reytingga oson o'tkaziladi; Kids kabinetida yulduz sifatida
  ko'rsatish mumkin.
* **Fayllar yopiq bucket'da**, faqat o'quvchining o'ziga, uni tekshiradigan o'qituvchiga va
  xodimlarga qisqa muddatli havola bilan beriladi. Ruxsat etilgan turlar ro'yxati bor (rasm,
  hujjat, arxiv, kod, Scratch `.sb3`); dastur fayllari (`.exe` va h.k.) qabul qilinmaydi.
  **Yuklangan kod serverda hech qachon ishga tushirilmaydi** va arxivlar ochilmaydi.
* **Kimga ko'rinadi:** o'qituvchi — o'z guruhlari va o'z kurslari javoblari; Admin — hammasi
  (tekshira oladi); Menejer va Direktor — ko'radi.
* **"Vazifalar" sahifasi** o'quvchi uchun: qayta ishlash kerak → topshirilmagan → tekshirilmoqda →
  qabul qilingan. Topshirilmaganlar faqat o'quvchi yetib kelgan darslar bo'yicha ko'rsatiladi
  (hali boshlanmagan 40 ta dars vazifasi bilan qo'rqitmaslik uchun).
* **Muddat ixtiyoriy.** Muddatdan keyin yuborish mumkin, javob "kechikkan" deb belgilanadi.
* **Statistika (10-qadam):** "48 soatdan beri tekshirilmagan uy vazifalari" muammolar
  ro'yxatiga qo'shiladi.

**Backend**

| # | Vazifa |
|---|---|
| 1 | `homework` app: `Assignment` (dars, sarlavha, topshiriq, muddat), `Submission` (vazifa, o'quvchi, urinish raqami, holat, izoh, kod va tili, havola, baho, o'qituvchi izohi, kim va qachon tekshirdi, kechikkan), `SubmissionFile` (yopiq fayl, nomi, hajmi, turi, rasmmi) |
| 2 | Admin: dars sahifasida "Uy vazifasi" bloki (o'qituvchi faqat o'z kurslarida); "Uy vazifalari" ro'yxati (filtrlar, fayllar, tarix) |
| 3 | O'quvchi API: dars javobida vazifa va urinishlar; `POST` javob (multipart, fayl cheklovlari, bir vaqtda bitta tekshirilmayotgan urinish), tekshirilmaganini qaytarib olish, "Vazifalar" ro'yxati, fayl havolasi (huquq tekshiriladi) |
| 4 | O'qituvchi API: tekshirish navbati (eng eskisi tepada, guruh bo'yicha filtr), javob sahifasi, qaror (qabul — baho bilan, qaytarish — izoh bilan); guruh sahifasida har o'quvchining vazifalar statistikasi; `me`da `pending_reviews` |
| 5 | Xabarlar (10-qadam infratuzilmasi): yangi javob — o'qituvchiga, natija — o'quvchiga |
| 6 | Rollar: o'qituvchiga vazifa yaratish va o'z javoblarini ko'rish; nginx'da vazifa yuklash uchun 60 MB |
| 7 | Testlar: fayl cheklovlari, urinishlar, kim ko'radi va kim tekshiradi, qarorlar, xabarlar, admin |

**Frontend**

| # | Vazifa |
|---|---|
| 1 | Dars sahifasida "Uy vazifasi": topshiriq, holat, o'qituvchi izohi va bahosi, javob formasi (izoh, kod, havola, fayllar — rasm ko'rinishi bilan, yuklash foizi), urinishlar tarixi |
| 2 | "Vazifalar" sahifasi (o'quvchi) va menyuda bo'lim |
| 3 | O'qituvchi: menyuda "Tekshirish" (soni bilan), navbat sahifasi va javob sahifasi (kod, rasmlar, fayllar, tarix, qaror formasi, "keyingisi"); guruh sahifasida vazifalar ustuni |
| 4 | E2E: o'quvchi javob yuboradi → o'qituvchi baho qo'yadi → o'quvchi natijani ko'radi; axe |

**Chegaralar (keyinroq):** AI dastlabki tekshiruv (Claude kod haqida fikr yozadi, bahoni baribir
o'qituvchi qo'yadi) — Anthropic hisobi ishlagach, alohida kichik qadam; o'xshashlik (ko'chirma)
tekshiruvi; arxiv ichini platformada ko'rish; audio/video izoh; rubrika; ommaviy portfolio;
guruh bo'yicha alohida muddatlar.

**Tekshiruv:** pytest; E2E; o'quvchi va o'qituvchi sahifalarining skrinshotlari (telefon ham).


### 7A.9. 11-qadam natijalari (2026-09-29)

| Qism | Holat |
|---|---|
| Vazifa berish | Admin → dars sahifasida "Uy vazifasi" bloki (sarlavha, topshiriq, ixtiyoriy muddat). O'qituvchi faqat o'z kurslari darslariga qo'shadi |
| O'quvchi | Dars sahifasida: topshiriq, holat, o'qituvchi izohi va bahosi, javob formasi (izoh, kod va tili, havola, 5 tagacha fayl yoki rasm — tanlanganda ko'rinadi), yuklash foizi, tekshirilmaganini qaytarib olish, yuborilgan javoblar tarixi. Kabinetda **"Vazifalar"** sahifasi |
| Fayllar | Yopiq storage, qisqa muddatli havola; turlar ro'yxat bo'yicha, har biri 20 MB, jami 50 MB (nginx'da shu yo'l uchun 55 MB); rasm Pillow bilan tekshiriladi; kirill nomli fayllar asl nomi bilan yuklab olinadi. Kod ishga tushirilmaydi, arxiv ochilmaydi |
| O'qituvchi | Kabinetda **"Tekshirish"** (menyuda soni bilan): navbat (eng eskisi tepada, 48 soatdan oshgani qizil, guruh filtri), tekshirilganlar (30 kun), javob sahifasi — kod, rasmlar, fayllar, oldingi urinishlar, qaror: qabul (baho 0–100) yoki qaytarish (izoh bilan). Guruh sahifasida har o'quvchining vazifalari: qabul qilingan, o'rtacha baho, kutayotgani |
| Kim tekshiradi | Guruh ustozi — o'z guruhi, kurs ustozi — guruhsiz o'quvchilar, Admin — hammasi. Boshqa o'qituvchiga 404 |
| Xabarlar | Yangi javob — o'qituvchiga (kabinet va Telegram), natija — o'quvchiga (baho va izoh bilan) |
| Admin | "O'qish → Uy vazifalari" ro'yxati (faqat ko'rish, o'qituvchiga — o'zinikilari); admin bosh sahifasida "48 soatdan beri tekshirilmagan uy vazifalari" muammosi |

Tekshiruv: backend 474 test, ruff, mypy, OpenAPI; frontend typecheck, eslint, 54 Vitest;
**29 ta E2E** (yangi: o'quvchi izoh, kod va rasm bilan javob yuboradi → o'qituvchi baho qo'yadi →
o'quvchi natijani ko'radi; axe). Sinovda topilib tuzatildi: qabul qilingan javob mazmuni o'quvchiga ko'rinmasdi; `router.refresh()` paytida Next metadata'ni vaqtincha olib tashlaganda brauzer `/favicon.ico` so'rab 404 olardi — logodan `favicon.ico` qo'shildi. Skrinshotlar: forma, tekshirilayotgan javob, o'qituvchi navbati va
javob sahifasi (tungi tema), telefonda natija.

**Sozlamalar:** arizalar Telegram guruhi ulandi (`TELEGRAM_LEADS_CHAT_ID`, bot — administrator,
guruhda 2 a'zo). Anthropic API 29-sentabr 14:38 da ham "credit balance is too low" qaytardi.


### 7A.10. 12-qadam: testlar va o'yinlar — batafsil vazifalar

Maqsad: o'quvchi darsni tushunganini qisqa test va o'yinli mashqlar bilan tekshiradi, darhol
javob va izoh oladi; o'qituvchi qaysi savol qiyin bo'lganini ko'radi. 10-qadamdan qolgan
faolsizlik eslatmalari ham shu qadamda.

**Qanday ishlaydi**

1. O'qituvchi admin'da darsga **test** qo'shadi. Savollarni bittalab yoki **"Tez kiritish"**
   maydoniga oddiy matn ko'rinishida bir yo'la yozadi (pastda namuna).
2. O'quvchi dars sahifasida "Testni boshlash"ni bosadi. Savollar bittadan chiqadi: javob beradi →
   **darhol** "to'g'ri / noto'g'ri", to'g'ri javob va o'qituvchi izohi. Ketma-ket to'g'ri javoblar
   seriyasi, yakunda foiz, **yulduzlar** (1–3) va xatolar ro'yxati.
3. Baholash **serverda**: savollar brauzerga javobsiz boradi, har bir javob alohida tekshiriladi
   va saqlanadi (sahifa yangilansa ham yo'qolmaydi). Qayta urinish cheklanmagan, eng yaxshi natija
   hisobga olinadi. O'tish bali bilan o'tilsa, dars "tugatildi" deb belgilanadi.
4. Dars ro'yxatida testli darslar yonida yulduzlar ko'rinadi; o'qituvchining guruh sahifasida
   har o'quvchining test natijasi; admin'da har savol bo'yicha to'g'ri javoblar foizi.

| Savol turi | Qanday javob beriladi | Tez kiritishda |
|---|---|---|
| Bitta to'g'ri javob (ha/yo'q ham) | Variantni tanlaydi | `+ to'g'ri`, `- noto'g'ri` |
| Bir nechta to'g'ri javob | Bir nechtasini belgilaydi | bir nechta `+` |
| Matn bilan javob | Yozadi (katta-kichik harf va ortiqcha bo'shliq hisobga olinmaydi) | `= javob` (bir nechta variant mumkin) |
| **Tartiblash** (o'yin) | Qadamlarni yuqoriga/pastga suradi | `1. …`, `2. …` |
| **Moslashtirish** (o'yin) | Chapdagini o'ngdagiga bosib juftlaydi | `chap :: o'ng` |

Savolga kod parchasi (masalan, "bu kod nima chiqaradi?") va izoh (`> …`) qo'shish mumkin.

**Qarorlar**

* **Testlar darsga bog'lanadi.** Modul yoki bo'lim testi — videosiz, faqat testli dars.
* **Sozlamalar kam:** o'tish bali (70%), har urinishdagi savollar soni (bankdan tasodifiy),
  savollar tartibini aralashtirish. Variantlar har doim aralashtiriladi.
* **Yulduzlar:** 90% va undan yuqori — 3, o'tish bali — 2, 50% — 1. 14-qadamdagi XP shularga
  tayanadi.
* **Faolsizlik eslatmasi:** kursni boshlagan, lekin 3 va 7 kundan beri dars ko'rmagan, test yoki
  vazifa yubormagan o'quvchiga — kabinet va Telegram orqali keyingi dars havolasi bilan, har
  holat uchun bir marta, soat 10:00 da.

**Backend**

| # | Vazifa |
|---|---|
| 1 | `quizzes` app: `Quiz` (dars, sarlavha, o'tish bali, savollar soni, aralashtirish), `Question` (tur, matn, kod, izoh, tartib), `Choice` (matn, to'g'rimi, juft matni, tartib), `Attempt` (o'quvchi, savollar ro'yxati, foiz, yulduz, o'tdimi, tugagan vaqti), `Answer` (javob, to'g'rimi) |
| 2 | "Tez kiritish" formati parseri (xatolar qator raqami bilan) va baholash (5 tur) |
| 3 | API: urinishni boshlash (savollar javobsiz, aralashtirilgan), javob berish (natija, to'g'ri javob, izoh), yakunlash (foiz, yulduz, xatolar); dars javobida test holati (eng yaxshi natija, urinishlar soni), kurs dasturida har dars yulduzi |
| 4 | Admin: darsda "Test" bloki; test sahifasi — tez kiritish, savollar ro'yxati, har savol bo'yicha natija; savol sahifasi — variantlar. O'qituvchi faqat o'z kurslarida |
| 5 | O'qituvchining guruh sahifasi: har o'quvchining o'rtacha test natijasi va o'tgan testlari |
| 6 | Faolsizlik eslatmalari (beat, 10:00, 3 tilda) |
| 7 | Testlar: parser, har tur baholash, javoblar oldindan ko'rinmasligi, bir savolga ikki marta javob berib bo'lmasligi, boshqaning urinishi, eng yaxshi natija, dars tugatilishi, eslatmalar takrorlanmasligi |

**Frontend**

| # | Vazifa |
|---|---|
| 1 | Dars sahifasida test kartasi: savollar soni, eng yaxshi natija va yulduzlar, "Boshlash" / "Qayta urinish" |
| 2 | Test o'yini: savollar bittadan, 5 tur uchun javob berish (tartiblash — tugmalar bilan, moslashtirish — bosib juftlash), darhol natija va izoh, seriya, progress, yakuniy ekran (foiz, yulduzlar, xatolar). Klaviatura, ekran o'quvchi va `prefers-reduced-motion` hisobga olinadi; Kids kabinetida yirikroq |
| 3 | Dars ro'yxatida test yulduzlari |
| 4 | E2E: o'quvchi testni ishlaydi (bitta xato bilan), natija va yulduzlarni ko'radi; axe |

**Chegaralar (keyinroq):** kodni sandbox'da ishga tushirib tekshirish (Judge0) — xavfsizlik va
server talab qiladi; vaqt chegarasi, urinishlar limiti va yakuniy imtihon — sertifikatlar bilan;
xatolar uchun AI tushuntirishi va AI bilan savol tuzish — Anthropic hisobi ishlagach; qisman ball.

**Tekshiruv:** pytest; E2E; test o'yini va natija ekranining skrinshotlari (telefon, Kids).

### 7A.11. 12-qadam natijalari (2026-09-29)

| Qism | Holat |
|---|---|
| O'qituvchi | Admin → dars sahifasida **"Test"** bloki (sarlavha, o'tish bali, har urinishda savollar soni, aralashtirish); "o'zgartirish" havolasi yoki menyudagi **"Testlar"** test sahifasini ochadi: **"Tez kiritish"** (xatolar qator raqami bilan, yangi savollar oxiriga qo'shiladi), savollar ro'yxati (sudrab tartiblanadi), **har savol bo'yicha javoblar soni va to'g'ri foizi**. Savol sahifasida variantlar turga qarab tekshiriladi (masalan, bitta to'g'ri javobli savolda aynan bitta "to'g'ri"). Faqat o'z kurslari; "Test natijalari" — faqat ko'rish |
| O'quvchi | Dars sahifasida "Mini-test" kartasi: savollar soni, o'tish bali, eng yaxshi natija, yulduzlar, urinishlar; "Testni boshlash" / "Davom ettirish" / "Qayta ishlash". O'yin: savollar bittadan, **test yuritgichi uslubidagi qator** (✓ / ✗ / miltillovchi kursor — brend belgisi), ketma-ket to'g'ri javoblar seriyasi, har javobdan keyin darhol natija, to'g'ri javob va izoh; yakunda foiz, yulduzlar, "Xatolar ustida ishlash", "Keyingi dars". "Keyinroq davom ettirish" — javoblar saqlanadi (24 soat) |
| 5 tur | Bitta / bir nechta javob, matn (katta-kichik harf, ortiqcha bo'shliq va oxirgi tinish belgisi farq qilmaydi), **tartiblash** (↑/↓ tugmalari, fokus element bilan birga yuradi), **moslashtirish** (chapdagisi o'zi tanlanadi, juftlar bir xil harf va rangda). Klaviatura va ekran o'quvchi (harakatlar e'lon qilinadi), `prefers-reduced-motion`; SIFAT Kids kabinetida yirik va rangli |
| Xavfsizlik | Baholash serverda. Brauzer variantlarni baza ID si bilan emas, **shu urinishdagi o'rni** bilan ko'radi — sinovda topildi: ID lar yaratilish tartibida bo'lgani uchun tartiblashda javobni, moslashtirishda juftlarni ochib qo'yardi. Noto'g'ri formatdagi javob — 400 (oldin 500 bo'lardi); bitta savolga bir marta; boshqaning urinishi — 404; kursga yozilmagan — 403 |
| Natijalar | Eng yaxshi natija hisobga olinadi, o'tilsa dars "tugatildi". Yulduz: 3 — o'tdi va 90%+, 2 — o'tdi, 1 — 50%+ (2+ yulduz doim "o'tdi" degani). Kurs dasturida testli darslar yonida yulduzlar; o'qituvchining guruh sahifasida **"Testlar"** ustuni (o'tganlari, o'rtacha eng yaxshi natija). O'qituvchi savolni o'chirsa, u tugallanmagan urinishlar hisobiga kirmaydi |
| Eslatmalar | Har kuni 10:05 da kursni boshlagan, lekin 3–6 yoki 7–13 kundan beri o'qimagan (dars ko'rmagan, vazifa yoki test yubormagan) o'quvchiga keyingi dars havolasi — kabinet va Telegram, o'quvchi tilida, har tanaffusda har bosqich bir marta. Ikki haftadan keyin, kursni boshlamagan, tugatgan va muddati o'tganlarga yozilmaydi |

Tekshiruv: backend 543 test (yangi 69: parser, 5 tur baholash, javoblar oldindan ko'rinmasligi
va barqaror aralashtirish, davom ettirish, noto'g'ri format, eng yaxshi natija va yulduzlar, dars
tugatilishi, o'chirilgan savol, "boshidan boshlash", huquqlar, admin'da tez kiritish va variantlar tekshiruvi,
o'qituvchi faqat o'zinikini ko'rishi, eslatmalar), ruff, mypy, OpenAPI; frontend typecheck,
eslint, 65 Vitest; **33 ta E2E** (yangi: o'quvchi 5 turdagi savolni bitta ataylab xato
bilan ishlaydi → 80%, 2 yulduz, dars tugatildi; o'qituvchi natijani guruh sahifasida ko'radi;
telefonda to'xtatib davom ettirish; axe uchta holatda). Skrinshotlar: karta, savollar, natija
(yorug' va tungi), telefon, SIFAT Kids, o'qituvchining admin sahifasi.

Sinov va skrinshotlarda topilib tuzatildi: variant ID lari javobni ochib qo'yardi (yuqorida);
noto'g'ri formatdagi javob 500 berardi; "Boshidan boshlash"dan keyin kartada tashlab ketilgan eski
urinish "Davom ettirish" bo'lib chiqardi (endi faqat eng oxirgi urinish davom ettiriladi);
o'quvchi tanlagan to'g'ri variant yashil emas, oddiy "tanlangan" ko'rinishda qolardi (belgilanmagan
to'g'ri variant endi uzuq chiziq bilan); SIFAT Kids ranglari natija ranglarini bosib ketardi;
dars sahifasining yon panelida darslar ro'yxati kengayib, davomiylik ko'rinmay qolardi (oldindan
bor xato — ro'yxat ustuni `minmax(0, 1fr)`); admin statistikasi jadvali uslubsiz edi (endi Unfold
jadvali), savol variantlariga havola faqat sichqoncha ustida chiqardi (endi "Variantlar" ustuni).

## 7B. Yangi talablar (2026-09-29): bot, testlar, XP, referal, reyting

12-qadamdan keyin buyurtmachi yangi talablar berdi va kod yozishdan oldin hammasini aniq
kelishib olishni so'radi. Ikki bosqichli muhokamadan keyingi kelishilgan reja (29-sentabr).

| Talab | Qisqacha |
|---|---|
| Telegram bot | Ro'yxatdan o'tish, majburiy obuna, dars testlari, kunlik topshiriqlar, yangiliklar, xabarlar, do'stni taklif qilish |
| Video faqat saytda | Botda video yo'q |
| Darsdan keyin test — botda | Sayt botga yo'naltiradi; test 70% va undan yuqori bo'lsa keyingi dars ochiladi |
| Offlayn guruhlar | Ustoz "dars o'tildi" deb belgilaydi — shu darsning testi va vazifalari chiqadi |
| Kunlik topshiriqlar va shtraflar | Har kuni har xil topshiriqlar; XP beradi va ayiradi. XP faqat saytda ko'rinadi |
| Oylik imtihon | Har oy oxirida 20 ta test + 5 ta amaliy topshiriq |
| Referal | Do'stni taklif qilish: coin + chegirma |
| Reyting | O'quvchilar reytingi (saytda) |
| Yangiliklar | Admin paneldan qo'shilgan yangilik botdagi hammaga boradi |
| SIFAT Kids | Oxirida, boshqa g'oyalar bilan |

**Buyurtmachi qarorlari:**

| Savol | Qaror |
|---|---|
| Bot | **Yangi bot, hammasi bitta botda** (AI maslahatchi ham). **Oddiy tugmalar, Mini App yo'q** — video faqat saytda |
| Test qayerda ishlanadi | **Asosan botda**; saytda zaxira ("Testni shu yerda ishlash") |
| Kunlik test | **Har kuni har xil topshiriqlar va shtraflar** |
| Shtraflar | **Faqat XP ayiriladi**, 0 dan pastga tushmaydi, ustoz bekor qila oladi; test yiqilgani uchun shtraf yo'q |
| Referal | **Do'stni taklif qilish, coin + chegirma** |
| Qo'shimchalar | Sertifikat va davomat — hozir; ota-ona rejimi — Kids bilan oxirida |
| Keyinga | **SIFAT Kids, ota-ona rejimi, o'yinlar, Kids ligasi**; Payme/Uzum va promo-kodlar |

### 7B.1. Qanday ishlaydi

**Bot — yangi bot, oddiy tugmalar.** Menyu: Kurslarim (saytga bir bosishda kirish), Testlar,
Bugungi topshiriqlar, Jadval, Do'stni taklif qilish, Savol berish (AI maslahatchi, kerak bo'lsa
menejer), Sozlamalar (til, yangiliklar). Video va XP botda yo'q — saytda.

**Ro'yxatdan o'tish — bitta akkaunt, ikki eshik.**

* **Saytdan** (hozirgidek): telefon → SMS kod → ism; Google yoki Telegram tugmasi bilan ham.
* **Botdan:** /start → majburiy obuna → "📱 Telefonni yuborish" (raqamni Telegram tasdiqlaydi —
  SMS kerak emas) → ism (Telegram'dagi ism taklif qilinadi) → tayyor.
* **Bir telefon — bitta akkaunt:** saytda ro'yxatdan o'tgan odam botga o'sha raqamni yuborsa,
  akkaunti o'zi ulanadi.
* **Sayt → bot:** havolada bir martalik kalit — bot odamni o'zi taniydi. **Bot → sayt:** bir
  martalik kirish havolasi — Telegram ichidagi brauzerda ham parol so'ralmaydi.
* Offlayn o'quvchini menejer admin'da qo'shadi (telefon va guruh); o'quvchi botga raqamini
  yuborishi bilan akkaunti, guruhi va darslari tayyor.
* Parol ixtiyoriy (SMS kod yoki Telegram bilan kiriladi). Referal havolasi ikkala eshikda ham
  ishlaydi. Xodim akkauntlari bot orqali ulanmaydi — faqat kabinetdan.

**Majburiy obuna.** /start va har bir menyu bosilganda bot kanal a'zoligini tekshiradi; obuna
bo'lmaganga "Kanalga o'tish" va "✅ Tekshirish". Bot kanalda administrator bo'lishi shart.
Kanallar ro'yxati admin'da (tavsiya — bitta kanal). Saytda obuna talab qilinmaydi.

**Darsdan keyingi test (onlayn, o'z tezligida o'qiydiganlar).**

1. Video tugaganda saytda katta "Testni Telegram'da ishlash" tugmasi (bir bosishda Telegram
   ochiladi) va kichik "Saytda ishlash" havolasi (zaxira).
2. Bot savollarni tugmalar bilan beradi: bitta javob, bir nechta javob, yozma javob (tartiblash va
   moslashtirish ham bo'ladi, lekin chatda kamroq ishlatiladi).
3. **70% va undan yuqori** — keyingi dars ochiladi, "Keyingi darsga" tugmasi (bir martalik kirish
   havolasi). Kam bo'lsa — qayta urinish; har safar savollar bankidan boshqa savollar, to'g'ri
   javoblar test o'tilgandan keyin ko'rsatiladi (aks holda ikkinchi urinishda hamma o'tib ketadi).
4. O'tish bali admin'da har test uchun sozlanadi.

**Offlayn guruhlar.** Ustoz jadvaldagi darsga mavzuni belgilab, "Dars o'tildi" deydi — shu dars
guruh uchun ochiladi: testi botga keladi (darsga kelmaganlarga ham — yetib olishi uchun), uy
vazifasi saytda chiqadi. Offlaynda test keyingi darsni to'smaydi (darsni ustoz olib boradi);
natija ustozga va reytingga boradi.

**Kunlik topshiriqlar va shtraflar** (qiymatlar namunaviy, admin'da sozlanadi):

* Har kuni ertalab bot "Bugungi topshiriqlar"ni yuboradi — 3 ta, har kuni boshqacha, o'quvchi
  qayerga yetganiga qarab: keyingi darsni ko'rish (+10), dars testidan o'tish (+15), takrorlash —
  botda 5 ta savol (+5), uy vazifasini topshirish (+20), offlaynda darsga vaqtida kelish (+10).
  Uchalasi bajarilsa — bonus (+10) va kunlik seriya davom etadi.
* **Shtraflar:** kunlik topshiriq bajarilmadi (−5), darsga sababsiz kelmadi (−15), kechikdi (−5),
  uy vazifasi muddatidan kechikdi (−10).
* Test yiqilgani uchun shtraf yo'q — shtraf harakatsizlik uchun, xato uchun emas. XP 0 dan pastga
  tushmaydi. Har shtraf sababi bilan ko'rinadi; ustoz yoki admin bekor qila oladi (masalan,
  kasallik). XP va tarixi — saytda, kabinetda.

**Yangiliklar.** Admin panelda yangilik (matn, rasm, havolali tugma) → kabinetga va **botdagi
hammaga** (/start bosganlarning hammasi, ro'yxatdan o'tmaganlar ham). 22:00–09:00 da yozilgani
ertalab ketadi. Botda "Yangiliklarni o'chirish" tugmasi. Telegram cheklovi — sekundiga ~30 xabar
(10 000 kishiga ~6–7 daqiqa), navbat bilan yuboriladi.

**Referal — do'stni taklif qilish, coin + chegirma** (foizlar admin'da):

* har kimning shaxsiy havolasi (bot va sayt); kim taklif qilgani ro'yxatdan o'tishda yoziladi
  (14-qadamdan boshlab; mukofotlar 16-qadamda — oldingi takliflar ham hisobga olinadi);
* do'st telefonini tasdiqlab, birinchi darsni tugatsa — taklif qilganga coin;
* do'st **birinchi to'lovda chegirma** oladi (standart 10%);
* do'st to'lov qilsa — taklif qilganga ko'proq coin va **keyingi to'lovi uchun chegirma kuponi**
  (standart 10%; bitta to'lovga bitta kupon);
* o'zini taklif qilib bo'lmaydi; chegirma Click to'lovidan oldin buyurtma summasiga qo'llanadi.

**Reyting (saytda).** Haftalik, oylik va umumiy; guruh va kurs bo'yicha. Faqat ism va
familiyaning bosh harfi; eng yaxshi 10 ta va o'z o'rni ko'rinadi; reytingdan yashirinish mumkin.
Haftalik g'oliblar kanalga e'lon qilinadi (ixtiyoriy).

**Oylik imtihon va sertifikat.** Har oy oxirida 20 ta test (40 daqiqa, bitta urinish, javoblar
imtihon yopilgach) + 5 ta amaliy topshiriq (o'qituvchi baholaydi); natija — test 50% + amaliy 50%,
o'tish 60% (standart qiymatlar). Test qismi botda yoki saytda bo'lishi — 15-qadam oldidan
kelishiladi. Sertifikat — kurs tugatilganda (darslar, testlar, vazifalar, imtihonlar o'rtachasi),
PDF va QR bilan tekshirish.

### 7B.2. Qolgan ishlar tartibi

| Qadam | Nima | Hajmi |
|---|---|---|
| **13** ✅ | **Jonli darslar va davomat:** jadval (haftalik jadvaldan avtomatik), eslatmalar, "Qo'shilish", yozuv, davomat; offlaynda **"Dars o'tildi"** — dars guruh uchun ochiladi, test va vazifa chiqadi | o'rta–katta |
| **14** ✅ | **Telegram bot** (yangi bot, oddiy tugmalar): ro'yxatdan o'tish (telefon), majburiy obuna, sayt ↔ bot bir bosishda, **dars testlari botda va 70% bilan keyingi dars** (saytda zaxira), yangiliklar botdagi hammaga, xabarlar, AI maslahatchi, referal havolalari | katta |
| **15** ✅ | **Oylik imtihon va sertifikat** | o'rta–katta |
| **16** ✅ | **XP:** kunlik topshiriqlar, shtraflar, seriya; **reyting** (saytda); **referal mukofotlari** (coin + chegirma) | o'rta–katta |
| **17** ✅ | **Coin do'koni:** sovg'alar, zaxira, buyurtma va topshirish | o'rta |
| **18** | **Ishga tushirish:** server, domen, HTTPS, bot webhook, Click va Eskiz, zaxira nusxa, monitoring. Sayt va bot ishlayapti (Contabo, umumiy server rejimi); Click, Eskiz va `media.sifatedu.uz` — kutilmoqda | o'rta |
| **19** ✅ | **Yangi kelganlar yo'li** (§7D): manba (Instagram va boshqalar), yo'nalish → daraja testi → 15% yoki 25% kupon (72 soat) → ariza menejerga → eslatmalar. Qo'llanma — `docs/yangi-kelganlar.md` | o'rta–katta |
| **20** ✅ | **AI maslahatchi — Gemini** (§7D): Claude olib tashlanadi; samimiy maslahatchi, bilim bazasi, e'tirozlar, kupon va test taklifi. Qo'llanma — `docs/ai-maslahatchi.md` | o'rta–katta |
| **21** ✅ | **Onlayn guruhlar Zoom orqali, videosiz** (§7D): darslar o'qituvchi «Dars o'tildi» deganda ochiladi | kichik |
| **22** ✅ | **Guruhlarga kunlik test** (§7D): 07:00 → 23:00, kamida 20 savol, natija darhol, javoblar 23:00 da, XP va guruh reytingi | o'rta–katta |
| **23** | **Ko'p markazli platforma — asos** (§7C): har markaz bazada alohida sxemada, domen bo'yicha aniqlanadi; markaz sozlamalari va shifrlangan kalitlari; fon vazifalari, kesh va fayllar markaz bo'yicha; super admin; Sifat Edu — birinchi markaz; markazlar orasida ma'lumot sizmasligi testlari | katta |
| **24** | **Markazning o'z brendi va integratsiyalari:** nom, logo, ranglar; landing va hujjatlar admin'dan; o'z Telegram boti (ko'p botli webhook); o'z Click va Eskiz; AI budjeti. Frontend sozlamalari build paytida emas, har so'rovda domen bo'yicha | katta |
| **25** | **SaaS ishlatish:** markaz domeni va avtomatik HTTPS, yangi markazni 10 daqiqada ulash, tarif cheklovlari va foydalanish hisobi, obuna to'lovlari, markazlar uchun qo'llanma | o'rta–katta |
| **Oxirida** | **SIFAT Kids** (yangi g'oyalar), ota-ona rejimi, o'yinlar, Kids ligasi — boshidan ko'p markazli | — |

Mini App bo'lmagani uchun botni shu kompyuterda sinab bo'ladi (polling rejimi) — test server
faqat ishga tushirishda kerak.

### 7B.3. Keyinroq

SIFAT Kids (yangi g'oyalar bilan), ota-ona rejimi, o'yinlar (duel, blits, klaviatura trenajyori,
turnirlar), Kids ligasi, Payme va Uzum, to'liq promo-kod tizimi, Mini App, Telegram ichki to'lovi,
haftalik maqsad, dars ostida savol-javob, kurs sharhlari.

### 7B.4. Sizdan kerak

* **Kanal** havolasi va botni kanalga **administrator** qilish (14-qadam).
* **Yangi bot:** BotFather'da yaratib, **token** berish; bot rasmi va qisqa tavsif (14-qadam).
* XP, shtraf va referal qiymatlarini tasdiqlash (16-qadamgacha; namunaviy qiymatlar bilan
  boshlanadi), coin sovg'alari ro'yxati (17-qadamgacha).
* Server va domen — ishga tushirishda (18-qadam).

### 7B.5. Texnik eslatmalar

* Bot havolalari: `t.me/<bot>?start=<payload>` (64 belgigacha): test — bir martalik `q_<token>`,
  referal — `r_<kod>`, akkauntni ulash — `c_<token>` (bor). Botdan saytga — bir martalik kirish
  tokeni (Redis, ~10 daqiqa, bir marta), sessiya ochadi.
* Bot obunachilari (`BotSubscriber`: chat, til, obuna holati, bloklagan) — yangiliklar
  ro'yxatdan o'tmaganlarga ham boradi; "Yangiliklarni o'chirish" hisobga olinadi.
* A'zolik: `getChatMember` (bot kanalda administrator), natija Redis'da ~10 daqiqa.
* Darslar ochilishi (`access.can_open_lesson`): onlayn — oldingi darsning testi o'tilgan bo'lsa;
  offlayn guruh — ustoz "dars o'tildi" deb belgilagan bo'lsa. Botdagi test 12-qadamdagi
  baholash va `Layout` dan foydalanadi (inline tugmalar); javoblar urinish o'tilgach ko'rsatiladi,
  savollar bankidan tasodifiy.
* XP: o'zgarmas yozuvlar (`XPTransaction`: +/−, sabab, bekor qilingan), balans 0 dan past emas;
  kunlik topshiriqlar har kuni ertalab tuziladi, kechasi yakunlanadi.
* Referal: kod bitta, faqat ro'yxatdan o'tishda yoziladi; mukofot faollashgandan keyin; chegirma
  `Order.amount` ga Click'dan oldin, chek chegirmali narx bilan.

### 7B.6. 13-qadam: jonli darslar va davomat — batafsil vazifalar

Maqsad: guruh darslari jadvalda bo'ladi, o'quvchi eslatma oladi va bir bosishda darsga qo'shiladi;
o'qituvchi davomatni telefondan belgilaydi, kelmaganlar xabar oladi, rahbar muammoni ko'radi.
Offlayn guruhda ustoz "Dars o'tildi" deb belgilagan dars ochiladi.

**Qanday ishlaydi**

1. Menejer yoki o'qituvchi guruhga **haftalik jadval** qo'yadi (masalan, Du/Chor/Ju 18:00, 90
   daqiqa), onlayn guruhga doimiy Meet/Zoom havolasi, offlayn guruhga xona. Tizim har kecha 14 kun
   oldinga **darslarni o'zi yaratadi**; bittasini o'zgartirish yoki bekor qilish mumkin.
2. **O'quvchi** kabinetda "Jadval" sahifasida va bosh sahifada yaqin darsni ko'radi; onlayn darsda
   "Qo'shilish" tugmasi dars boshlanishidan 15 daqiqa oldin ochiladi. O'tgan darslar — davomat
   holati va yozuv havolasi bilan.
3. **Eslatmalar:** dars kuni oldindan (24 soat ichida) va 30 daqiqa oldin — kabinet va Telegram;
   bekor qilinsa yoki yozuv qo'shilsa — xabar.
4. **Davomat:** o'qituvchi dars sahifasida har o'quvchini belgilaydi: keldi / kechikdi / kelmadi /
   sababli ("Hammasi keldi" tugmasi bilan). Onlayn darsda "Qo'shilish"ni bosganlar oldindan
   "keldi" deb belgilanadi — o'qituvchi tasdiqlaydi. Kelmaganlarga dars tugagach xabar.
5. **"Dars o'tildi" (offlayn):** o'qituvchi darsga mavzuni (kurs darsini) belgilaydi — shu dars
   guruh o'quvchilari uchun ochiladi, "Yangi dars ochildi: test va vazifa" xabari boradi (14-qadamdan
   test botga keladi). Offlayn o'quvchiga ustoz ochmagan darslar yopiq.
6. **Nazorat:** guruh sahifasida har o'quvchining davomat foizi (30 kun); ketma-ket 2 marta
   kelmaganlar — admin bosh sahifasidagi "muammolar"da.

**Qarorlar**

* Google Meet API ishlatilmaydi — havola qo'lda qo'yiladi.
* Yozuv — havola (YouTube yopiq, Google Drive va h.k.); platformaga yuklash — keyinroq.
* "Qo'shilish" platforma orqali o'tadi (havola faqat guruh a'zolariga, bosilgani yoziladi).
* Davomatni guruh o'qituvchisi, menejer va admin belgilaydi; direktor — ko'radi.

**Backend**

| # | Vazifa |
|---|---|
| 1 | `live` app: `ScheduleSlot`, `LiveLesson` (guruh, boshlanish, davomiylik, onlayn/offlayn, havola, xona, mavzu-dars, yozuv, izoh, bekor qilingan), `Attendance`. Guruhga doimiy havola va xona |
| 2 | Jadvaldan darslar: har kecha 14 kun oldinga (takrorlanmaydi, bekor qilingani qaytmaydi); jadval o'zgarsa — moslanadi |
| 3 | API: jadval (yaqin / o'tgan), "Qo'shilish" (a'zolik va vaqt oynasi, bosilgani yoziladi); o'qituvchi: dars va ro'yxat, davomat, bekor qilish, yozuv va izoh, **"Dars o'tildi"** |
| 4 | **Offlayn guruhda dars ochilishi**: `GroupLesson` (guruh, dars, kim, qachon); `access.can_open_lesson` offlayn guruh o'quvchisiga faqat ochilgan darslarni beradi |
| 5 | Xabarlar: eslatmalar (beat har 5 daqiqa), bekor qilindi, yozuv qo'shildi, darsda bo'lmadingiz, yangi dars ochildi — 3 tilda, takrorlanmaydi |
| 6 | Admin: guruh sahifasida haftalik jadval, havola va xona; "Jonli darslar" (davomat soni, bekor qilish); davomat ro'yxati. O'qituvchi — faqat o'z guruhlari |
| 7 | Guruh sahifasi: davomat foizi va darslar; admin "muammolar": ketma-ket 2 marta kelmaganlar; `me` da jadval borligi |
| 8 | Testlar |

**Frontend**

| # | Vazifa |
|---|---|
| 1 | "Jadval" sahifasi: kunlar bo'yicha yaqin darslar, "Qo'shilish", o'tgan darslar (davomat, yozuv, izoh). Menyuda "Jadval" (guruhi borlarga) |
| 2 | Bosh sahifada "Keyingi dars" kartasi |
| 3 | O'qituvchi: guruh sahifasida darslar va davomat ustuni; dars sahifasi — telefonda qulay davomat, "Dars o'tildi", yozuv havolasi, bekor qilish |
| 4 | E2E va skrinshotlar |

### 7B.7. 13-qadam natijalari (2026-09-30)

| Qism | Holat |
|---|---|
| Jadval | Admin → guruh sahifasida **haftalik jadval** (hafta kuni, soat, davomiylik), doimiy Meet/Zoom havolasi yoki xona. Darslar har kecha 01:30 da 14 kun oldinga o'zi yaratiladi; jadval yoki havola o'zgarsa kelgusi darslar moslanadi (qo'lda o'zgartirilgan, bekor qilingan va davomati bor darslarga tegilmaydi, ID lar saqlanadi — eslatmalar takrorlanmaydi). "Jonli darslar" bo'limi: holat (rejada / ketmoqda / o'tdi / bekor), davomat soni, tanlanganlarni bekor qilish |
| O'quvchi | Menyuda **"Jadval"** (guruhi borlarga): kunlar bo'yicha yaqin darslar ("Bugun", "Ertaga"), **"Qo'shilish"** — boshlanishidan 15 daqiqa oldin o'zi yoqiladi, platforma orqali Meet'ga yo'naltiradi va kelganini "Keldi" / "Kechikdi" deb yozadi; o'tgan darslar — davomat holati, o'qituvchi izohi, yozuv havolasi. Bosh sahifada **"Keyingi jonli dars"** kartasi |
| Eslatmalar | Kabinet va Telegram, 3 tilda: dars kuni oldindan (24 soat ichida) va 30 daqiqa oldin (o'qituvchiga ham), bekor qilindi (sababi bilan; o'qituvchi o'zi bekor qilsa — unga emas), yozuv qo'shildi, **darsda bo'lmadingiz** (dars tugagach 15 daqiqadan keyin — xatoni tuzatishga ulgurish uchun), **yangi dars ochildi**. Har biri bir marta |
| O'qituvchi | Guruh sahifasida **davomat ustuni** (30 kun) va jonli darslar ro'yxati. Dars sahifasi (telefonda qulay): 4 holatli davomat, "Qolganlar — keldi", **"Dars o'tildi"** (mavzu tanlash, xato bo'lsa qaytarish), izoh va yozuv havolasi, boshlanmagan darsni bekor qilish |
| "Dars o'tildi" | Offlayn guruh o'quvchisiga test va uy vazifasi ustoz belgilagan **eng oxirgi dargacha** ochiladi (oldingilarni bittalab belgilash shart emas); qolgan darslarda "Test va uy vazifasi ustoz bu darsni guruhda o'tgach ochiladi" yozuvi, test boshlash va vazifa yuborish API da ham yopiq, "Vazifalar" ro'yxatida ko'rinmaydi. Video va materiallar ochiq. Menejer admin'da guruh sahifasidagi "O'tilgan darslar"da qo'lda ham belgilaydi (o'quvchilarga xabar bilan). Onlayn va guruhsiz o'quvchilarga cheklov yo'q |
| Nazorat | Admin bosh sahifasida **"Ketma-ket 2 marta darsga kelmagan o'quvchilar"**; davomat ro'yxati (o'qituvchiga — faqat o'z guruhlari) |
| Huquqlar | Davomat, bekor qilish, yozuv, "Dars o'tildi" — guruh o'qituvchisi, menejer, admin; direktor — faqat ko'radi; boshqa guruh — 404; "Qo'shilish" — faqat to'lov muddati o'tmagan guruh a'zolari va o'qituvchi |

Tekshiruv: backend **583 test** (yangi 40: jadvaldan yaratish va moslash, Toshkent vaqti, "Qo'shilish" oynasi va yo'naltirish, a'zolik, davomat va xabarlar, eslatma vaqtlari, bekor qilish, yozuv, "Dars o'tildi" va vazifalar ochilishi, admin, muammolar), Django 6.0 ogohlantirishlari xato sifatida; ruff, mypy, OpenAPI; frontend typecheck, eslint, **69 Vitest**; **38 ta E2E** (yangi: o'quvchi keyingi darsni ko'radi va qo'shiladi → Meet'ga yo'naltirish, yozuv; o'qituvchi davomat va "Dars o'tildi"; o'quvchi holati va "Yangi dars ochildi" xabari; telefonda davomat; axe).

Sinovda topilib tuzatildi: dars sahifasidagi yon panel (oldindan bor xato) kengayib ketardi — 12-qadamda tuzatilgan; asosiy tugmaning hover holati ochroq qizil bo'lgani uchun oq matn kontrasti tushardi — hamma joyda to'qroq qilindi; "Bekor qilish" tugmasining tayyor "destructive" uslubida kontrast yetmasdi; `StudyGroup` formasida havolalar uchun Django 6.0 ogohlantirishi (`https` standart). Ish paytida Docker VM qotib qoldi (4 GB xotira) — buyurtmachi ruxsati bilan qayta ishga tushirildi.

### 7B.8. 14-qadam: Telegram bot — batafsil vazifalar

Maqsad: yangi bot — ro'yxatdan o'tish (SMS'siz), majburiy obuna, dars testlari (70% bilan keyingi
dars ochiladi), jadval, yangiliklar botdagi hammaga, do'stni taklif qilish, AI maslahatchi; sayt
bilan bot o'rtasida bir bosishda o'tish. Mini App yo'q — oddiy tugmalar.

**Qanday ishlaydi**

1. **/start** → til (bir marta) → majburiy obuna → "📱 Telefonni yuborish" (oferta va maxfiylik
   siyosati eslatmasi bilan) → akkaunt ochiladi yoki mavjudiga ulanadi → menyu.
2. **Menyu:** 📚 Kurslarim (davom ettirish — saytga bir bosishda), 📝 Testlar, 📅 Jadval
   ("Qo'shilish" — kirish so'ralmaydi), 🎁 Do'stni taklif qilish, 💬 Savol berish (AI maslahatchi),
   ⚙️ Sozlamalar (til, yangiliklar, saytga kirish). Istalgan matn — AI maslahatchiga.
3. **Dars testi botda:** savollar tugmalar bilan (bitta / bir nechta / yozma javob, tartiblash,
   moslashtirish). Har javobdan keyin faqat ✅ yoki ❌. Yakunda natija; **o'tsa** — xatolar va to'g'ri
   javoblar, izohlar va "Keyingi darsga" tugmasi; **o'tmasa** — "Videoni qayta ko'rib, qayta urinib
   ko'ring" va "Qayta urinish".
4. **Saytda:** test kartasida katta "Telegram'da ishlash" (asosiy) va "Saytda ishlash" (zaxira).
   Video tugaganda test kartasiga olib boradi. Saytdagi testda ham to'g'ri javoblar test o'tilgach
   ko'rsatiladi.
5. **Onlayn o'quvchi:** keyingi dars oldingi testli darslar o'tilgach ochiladi (bepul/preview
   darslar va offlayn guruhlar bundan mustasno). Kurs dasturida yopiq dars — "Oldingi darsning
   testidan o'ting"; yopiq darsga to'g'ridan-to'g'ri kirilsa — tushuntirish va oldingi darsga havola.
6. **Offlayn:** ustoz "Dars o'tildi" deganda o'quvchiga botda "Testni boshlash" tugmali xabar.
7. **Yangiliklar:** admin → "Xabar yuborish"da "Botdagi hammaga ham" belgisi va rasm — /start
   bosganlarning hammasiga (ro'yxatdan o'tmaganlarga ham); 22:00–09:00 da yozilgani ertalab;
   botda "Yangiliklarni o'chirish".
8. **Do'stni taklif qilish:** shaxsiy havola (bot va sayt), taklif qilinganlar soni; kim taklif
   qilgani ro'yxatdan o'tishda yoziladi (mukofotlar — 16-qadamda).
9. **Kanallar** admin'da. Bot kanalda administrator bo'lmasa, obuna so'ralmaydi (o'quvchilar
   to'xtab qolmasin) va admin "muammolar"da ogohlantirish chiqadi.

**Xavfsizlik:** xodim (o'qituvchi, menejer, admin) akkaunti kontakt orqali ulanmaydi va botdan
saytga bir martalik kirish havolasi olmaydi. Havolalar bir martalik, 10 daqiqa. Faqat O'zbekiston
raqamlari (+998).

**Backend**

| # | Vazifa |
|---|---|
| 1 | `bot` app: `BotChat` (chat, foydalanuvchi, til, yangiliklar, bloklangan, taklif kodi, holat), `RequiredChannel` |
| 2 | Router: /start (`c_` ulash, `q_` test, `r_` referal), kontakt, menyu, tugmalar (callback), matn → AI maslahatchi. Webhook `callback_query` ni ham qabul qiladi |
| 3 | Ro'yxatdan o'tish va ulash (bir telefon — bitta akkaunt), oferta, majburiy obuna (`getChatMember`, kesh) |
| 4 | Botda test: 5 tur, holat saqlanadi, natija, ko'rib chiqish, qayta urinish; "Testlar" ro'yxati |
| 5 | Test qoidalari: onlayn — testdan o'tmaguncha keyingi dars yopiq (`access`), javoblar — faqat o'tilgach (sayt ham) |
| 6 | Bir martalik havolalar: sayt → bot (test), bot → sayt (kirish, keyingi dars, "Qo'shilish") |
| 7 | Yangiliklar: `Broadcast` ga "botdagi hammaga" va rasm; bot foydalanuvchilariga navbat bilan |
| 8 | Referal: `User.referral_code`, `User.referred_by`; sayt (`?ref=`) va bot (`r_`) |
| 9 | Admin: bot foydalanuvchilari (faqat ko'rish), kanallar; `bot_setup` buyrug'i (komandalar, tavsif) |
| 10 | Testlar (Telegram API soxta) |

**Frontend**

| # | Vazifa |
|---|---|
| 1 | Test kartasi: "Telegram'da ishlash" va "Saytda ishlash"; video tugaganda kartaga olib boradi |
| 2 | Test: javob paytida faqat to'g'ri/noto'g'ri; o'tgach — xatolar, to'g'ri javoblar, izohlar |
| 3 | Dasturda "testdan keyin ochiladi"; yopiq darsga kirilganda tushuntirish |
| 4 | `?ref=` havolasi eslab qolinadi va ro'yxatdan o'tishda yuboriladi |
| 5 | E2E va skrinshotlar |

**Chegara:** Telegram'ning o'zida to'liq sinov — yangi bot tokeni va kanal berilgach (hozircha
Telegram API soxta testlar bilan).

### 7B.9. 14-qadam natijalari (2026-09-30)

| Qism | Holat |
|---|---|
| Bot | Yangi `apps/bot`, oddiy tugmalar. /start → til (bir marta; saytdan kelganga — sayt tili) → majburiy obuna → **"📱 Telefonni yuborish"** (oferta va maxfiylik havolalari bilan). Kontakt — faqat o'z raqami va faqat +998. Raqam saytda bo'lsa — o'sha akkauntga ulanadi (eski Telegram almashtiriladi), bo'lmasa — akkaunt ochiladi (SMS'siz; saytga bot tugmasi bilan kiradi). Xodim raqami kontakt bilan ulanmaydi. Guruh va kanaldagi xabarlar e'tiborsiz |
| Menyu | 📚 Kurslarim (progress, keyingi dars — saytga bir bosishda), 📝 Testlar (ochiq va o'tilmagan, tugallanmagani "davom"), 📅 Jadval (yaqin darslar, "Qo'shilish" dars ochilganda), 🎁 Do'stni taklif qilish (shaxsiy havolalar, soni, "Do'stlarga yuborish"), 💬 Savol berish, ⚙️ Sozlamalar (til, yangiliklar, saytga kirish); /menu, /tests, /schedule, /settings, /help. Menyu tugmasi yoki test javobi bo'lmagan matn — **AI maslahatchiga** (alohida `ai` navbatida, bot tugmalari kutib qolmaydi) |
| Test botda | 5 tur tugmalar bilan (bitta va bir nechta javob, yozma, tartiblash, moslashtirish). Har javobdan keyin savol xabari "✅ To'g'ri" / "❌ Noto'g'ri" bilan yangilanadi. O'tsa — natija, xatolar (javobingiz, to'g'ri javob, izoh) va **"Keyingi darsga"**; o'tmasa — **"Qayta urinish"** va "Videoni ko'rish". Tugallanmagan test davom ettiriladi; eski xabardagi tugma bosilsa — "savol yopilgan"; bir odamning tez bosgan tugmalari navbat bilan ishlanadi |
| Sayt ↔ bot | Test kartasida **"Telegram'da ishlash"** (asosiy) va "Saytda ishlash": bir martalik havola (10 daqiqa), Telegram ulanmagan bo'lsa — shu akkauntga ulanadi. Botdagi saytga olib boradigan tugmalar **parolsiz kiritadi** (bir martalik; eskirsa — kirish sahifasi, keyin o'sha sahifa) — faqat raqami Telegram'da tasdiqlangan (kontakt yuborgan) chatga; xodimga — oddiy havola. Video tugaganda sahifa test kartasiga o'tadi |
| Test qoidalari | **Onlayn o'quvchi:** keyingi dars oldingi testli darsning testidan o'tilgach ochiladi (preview darslar, xodimlar, offlayn guruhlar — mustasno): video, materiallar va API ham yopiq. Kurs dasturida qulf "Oldingi darsning testidan o'ting", yopiq dars sahifasida tushuntirish va testli darsga havola; "Davom ettirish" testli darsga olib boradi. **Saytda ham** to'g'ri javoblar va izohlar test o'tilgach; o'tmasa — "Videoni qayta ko'rib, qayta urinib ko'ring" |
| Offlayn | "Dars o'tildi" xabarida Telegram'da **"📝 Testni boshlash"** — test botning o'zida ochiladi (darsda bo'lmaganlarga ham) |
| Yangiliklar | "Xabar yuborish"da **rasm** va **"Botdagi hammaga ham"** (faqat filtrsiz xabarda): ro'yxatdan o'tganlar odatdagidek (kabinet + Telegram), qolgan bot foydalanuvchilari — bot orqali; har kimga bir marta, yangiliklarni o'chirgan va botni bloklaganlarsiz; kechasi yozilgani 09:00 da. Tasdiqlash oynasida "Qo'shimcha: bot foydalanuvchilari" soni, natijada yetdi / yetmadi. Har xabar ostida "🔕 Yangiliklarni o'chirish". Rasm Telegram'ga bir marta yuklanadi |
| Referal | Shaxsiy kod (8 belgi): bot havolasi `start=r_KOD`, sayt `?ref=KOD` (cookie, 30 kun). Kim taklif qilgani ro'yxatdan o'tishda yoziladi — botda, saytda va Google/Telegram orqali; admin → foydalanuvchi: "Taklif qilgan", "Taklif qilganlari". Mukofotlar — 16-qadamda |
| Admin | **"Telegram bot"** bo'limi: Bot foydalanuvchilari (akkaunt, til, yangiliklar, bloklagan — faqat ko'rish), Majburiy kanallar (tekshiruv holati bilan). Bot kanalda administrator bo'lmasa, obuna so'ralmaydi va bosh sahifadagi muammolarda ogohlantirish chiqadi. Buyruqlar: `bot_setup` (menyu va tavsif 3 tilda), `telegram_webhook set` (tugmalar ham), `telegram_poll` |
| Huquqlar | Menejer — bot foydalanuvchilarini ko'radi, kanallarni boshqaradi; direktor — faqat ko'radi |

Tekshiruv: backend **637 test** (yangi 54: botda ro'yxatdan o'tish va ulash, majburiy obuna, 5 turdagi test tugmalar bilan, menyu, sayt ↔ bot havolalari, parolsiz kirish shartlari, yangiliklar va rasm, webhook; onlayn test qoidasi; javoblar o'tilgach; referal), Django 6.0 ogohlantirishlari xato sifatida; ruff, mypy, OpenAPI; frontend typecheck, eslint, **72 Vitest**; **40 ta E2E** (yangi: onlayn o'quvchi yopiq darsdan testli darsga o'tadi, taklif havolasi cookie'da; test — javob paytida faqat to'g'ri/noto'g'ri, o'tgach xatolar va izoh; axe).

Sinovda topilib tuzatildi: o'quv markazidagi umumiy kompyuterda "Telegram'da ishlash" bosilsa, u kompyuterdagi birovning Telegram'i o'quvchi akkauntiga ulanib, botdagi parolsiz kirish tugmalari bilan saytga kira olardi — parolsiz kirish faqat raqami tasdiqlangan chatga berildi; kurs dasturidagi yopiq darslar shaffoflik bilan xiralashtirilgani uchun matn kontrasti WCAG'dan past edi (axe) — qulf va uzuq chegara bilan almashtirildi; testlar `.env` dagi haqiqiy bot tokeni bilan Telegram'ga so'rov yuborishi mumkin edi — test sozlamalarida Telegram kalitlari bo'shatildi (CI dagi kabi); bot nomi (`getMe`) olinmasa har dars sahifasi 10 soniyagacha kutishi mumkin edi — xato 5 daqiqa eslab qolinadi (`TELEGRAM_BOT_USERNAME` yozilsa, so'rov umuman yo'q); admin'da kanal havolasi uchun Django 6.0 ogohlantirishi. Ish paytida Docker VM yana qotib qoldi (boshqa loyihaning konteyneri CPU'ni band qilgan) — buyurtmachi ruxsati bilan qayta ishga tushirildi.

**Chegara:** Telegram'ning o'zida to'liq sinov — yangi bot tokeni va kanal berilgach (hozircha Telegram API soxta server bilan sinaldi). Eski @sifatedu_managerbot ham shu kod bilan ishlaydi, lekin yangi bot tavsiya etiladi.

### 7B.10. 15-qadam: oylik imtihon va sertifikat — batafsil vazifalar

Qarorlar (2026-10-01): imtihonning test qismi **saytda ham, botda ham** (bitta urinish — qayerda
boshlansa, o'sha yerda davom etadi); sertifikat — saytdagi A4 sahifa, "PDF yuklab olish" brauzer
orqali (serverga yangi kutubxona o'rnatib bo'lmaydi — PyPI'ga ulanish yo'q; bu yetarli).

**Qanday ishlaydi**

1. **Tayyorlash:** kursda "Oylik imtihon" yoqiladi. Har oyning 20-kuni keyingi imtihon qoralamasi
   o'zi yaratiladi (oldingisining sozlamalari bilan) va o'qituvchilarga eslatma boradi. O'qituvchi
   yoki admin admin'da: savollar qaysi modullardan (standart — shu oy guruhlarda o'tilgan darslar
   modullari, bo'lmasa kursning testli modullari), **5 ta amaliy topshiriq**, sozlamalar (20 savol,
   40 daqiqa, o'tish 60%, test ulushi 50%) va "Tayyor". Tayyor bo'lmagan imtihon ochilmaydi — admin
   bosh sahifasida ogohlantirish.
2. **Ochilishi:** 25-kundan oy oxirigacha. Kursning faol o'quvchilariga (guruhli va guruhsiz)
   kabinet va botda "📝 Oylik imtihon ochildi" xabari.
3. **Test qismi** (saytda yoki botda, bitta urinish): tanlangan modullar testlaridan tasodifiy 20
   savol, 40 daqiqa (imtihon yopilishidan oshmaydi, vaqt serverda). Javob paytida to'g'ri/noto'g'ri
   ko'rsatilmaydi; vaqt tugasa — o'zi yakunlanadi. Foiz darhol, to'g'ri javoblar imtihon yopilgach.
4. **Amaliy qism** (saytda): 5 topshiriq — izoh, kod, havola, fayllar (uy vazifasidagi kabi);
   yopilguncha topshiriladi, qayta yuborilsa oxirgisi baholanadi.
5. **Baholash:** o'qituvchi kabinetda har topshiriqqa 0–100 va izoh. Natija = test × 50% + amaliy
   o'rtachasi × 50%, o'tish — 60%. Imtihon yopilgach va topshirilganlar baholangach natija yakuniy:
   o'quvchiga xabar. Topshirilmagan topshiriq — 0.
6. **Kelolmaganlar:** o'qituvchi o'quvchiga alohida muddat beradi — unga imtihon yana ochiladi.
7. **Sertifikat:** kursda yoqilgan bo'lsa, shartlar bajarilganda o'zi beriladi va xabar boradi:
   barcha darslar tugatilgan (offlayn guruhda — guruhda o'tilgan), testli darslarning testi
   o'tilgan, uy vazifalari qabul qilingan, imtihonlar o'rtachasi 60% dan yuqori (imtihon bo'lmagan
   bo'lsa — bu shart yo'q). Tarkibi: ism, kurs, sana, ball, unikal raqam, QR. Kabinetda
   "Sertifikatlarim"; ommaviy tekshirish sahifasi `/verify/<raqam>` ("Haqiqiy" / "Bekor qilingan");
   Telegram va LinkedIn'ga ulashish; admin bekor qiladi (sabab bilan).

**Backend**

| # | Vazifa |
|---|---|
| 1 | `exams` app: `Exam` (kurs + oy, modullar, sozlamalar, holat), `ExamTask` (5 ta), `ExamAttempt`/`ExamAnswer` (test — dars testlari mexanizmi bilan), `TaskAnswer` (+ fayllar), `ExamExtension`; `Course.monthly_exam`, `Course.certificate` |
| 2 | Xizmatlar: qatnashuvchilar, ochiq imtihon, test (boshlash, javob — natijasiz, vaqt, yakunlash), amaliy (topshirish, baholash), natija, alohida muddat |
| 3 | Beat: 20-kuni qoralama va eslatma; ochilish xabari; vaqti tugagan urinishlarni yopish; yakuniy natija xabarlari |
| 4 | API: o'quvchi (imtihonlar, test, topshiriqlar), o'qituvchi (natijalar, baho, muddat) |
| 5 | Bot: "📝 Testlar"da oylik imtihon, test oqimi (natijasiz, vaqt bilan) |
| 6 | `certificates` app: `Certificate`, shartlar, avtomatik berish, xabar, API (ro'yxat, ommaviy tekshirish), admin (bekor qilish) |
| 7 | Admin: imtihonlar (topshiriqlar, modullar, natijalar), sertifikatlar; muammolar: "imtihon tayyor emas", "baholanmagan amaliy topshiriqlar" |
| 8 | Testlar |

**Frontend**

| # | Vazifa |
|---|---|
| 1 | Kabinet: "Oylik imtihon" kartasi; imtihon sahifasi — test (taymer), 5 topshiriq, natija |
| 2 | O'qituvchi: imtihon natijalari va baholash sahifasi |
| 3 | "Sertifikatlarim"; sertifikat / tekshirish sahifasi (A4, QR, PDF, ulashish) |
| 4 | E2E va skrinshotlar |

### 7B.10a. 15-qadam natijalari (2026-10-01)

| Qism | Holat |
|---|---|
| Imtihon | Yangi `apps/exams`: kurs + oy, savol modullari, 5 tagacha amaliy topshiriq, sozlamalar (savollar soni, vaqt, o'tish bali, test ulushi), qoralama/tayyor. 20-kuni qoralama o'zi yaratiladi (oldingi sozlamalar, shu oy guruhlarda o'tilgan modullar) va ustozlarga xabar; tayyor bo'lmagan imtihon ochilmaydi (topshiriq yoki savol bo'lmasa admin'da qoralamada qoladi), 5 kun qolganda admin muammolarida ogohlantirish |
| Test qismi | Bitta urinish — saytda yoki botda (qayerda boshlansa, o'sha yerda davom). Savollar tanlangan modullar testlaridan tasodifiy, vaqt serverda (sahifa yopilsa ham ketadi; tugasa beat 5 daqiqada yopadi). Javob paytida to'g'ri/noto'g'ri aytilmaydi ("Javob saqlandi"), savolni **keyinga qoldirish** mumkin; foiz darhol, to'g'ri javoblar va izohlar imtihon (yoki alohida muddat) yopilgach |
| Amaliy qism | Uy vazifasidagi forma (izoh, kod, havola, 5 tagacha fayl, yuklash foizi) — imtihon ochiq va baholanmagan bo'lsa yangilanadi |
| O'qituvchi | Guruhlarim → "Oylik imtihonlar" → jadval (o'quvchi × topshiriq): katak — javob va baho (0–100, izoh), saqlangach keyingi baholanmagan javob ochiladi; kelolmaganga **alohida muddat** (yopilgandan keyin 45 kungacha). Kurs ustozi hamma o'quvchini, guruh o'qituvchisi — o'z guruhini ko'radi. Qoralama imtihonda "Admin panelda tayyorlash" havolasi |
| Natija | Test × ulush + amaliy o'rtachasi × qolgani, o'tish 60%. Imtihon yopilib, topshirilganlar baholangach — yakuniy: o'quvchiga xabar (kabinet + Telegram) |
| Bot | "📝 Testlar"da ochiq imtihon eng tepada → shartlar va "▶️ Boshlash" (vaqt shu tugma bilan) → savollar dars testidagi tugmalar bilan, har javobdan keyin faqat "✔️ Javob saqlandi" va qolgan vaqt → yakunda foiz va saytga (amaliy qism) tugma |
| Sertifikat | Yangi `apps/certificates`: shartlar (darslar — offlayn guruhda guruhda o'tilgan; testlar; qabul qilingan vazifalar; imtihonlar o'rtachasi ≥ 60%, imtihon bo'lmasa — shart yo'q) har o'qish hodisasidan keyin va har kecha tekshiriladi; berilganda xabar. Raqam `SE-YYMM-XXXXXX`. Kabinet → "Sertifikatlar" (qolgan shartlar bilan); ommaviy `/verify/<raqam>`: haqiqiy / bekor qilingan, A4 varaq (raqamdan chiziladigan "nuqtalar yo'li", QR — shu sahifaga), "PDF yuklab olish" (chop etish oynasi, A4 albom), Telegram va LinkedIn'ga ulashish. Admin: bekor qilish (sabab tekshirish sahifasida) va qaytarish |
| Umumiy | O'qish hodisalari (`apps/core/events.py`: dars tugatildi, test o'tildi, vazifa topshirildi/qabul qilindi, imtihon yakunlandi) — sertifikat va 16-qadamdagi XP shularni tinglaydi |

Tekshiruv: backend **672 test** (yangi 35: imtihon — bitta urinish, natijasiz javob, server vaqti, beat yopishi, alohida muddat, baholash va yakuniy natija, yopilgach javoblar, 20-kungi qoralama va ochilish xabari, API va ruxsatlar, admin "Tayyor" tekshiruvi; bot — imtihon oqimi, saytda boshlanganini davom ettirish, vaqt tugashi; sertifikat — shartlar, offlayn guruh, imtihon o'rtachasi, hodisadan berilishi, tekshirish API, admin bekor qilish); ruff, mypy, OpenAPI; frontend typecheck, eslint, **85 Vitest** (taymer, savollar orasida yurish, sertifikat yo'li); **47 ta E2E** (yangi 7: o'quvchi imtihon testini natijasiz ishlaydi — taymer, savolni keyinga qoldirish, 100%, amaliy topshiriq; o'qituvchi jadvaldan baholaydi; o'quvchi bahoni ko'radi; sertifikatni tekshirish sahifasi (QR, ulashish, topilmagan raqam, telefonda); kabinetdagi sertifikatlar; Telegram orqali kirishdan qaytish sahifasi; axe). Skrinshotlar va A4 PDF bilan ko'zdan kechirildi.

Sinovda topilib tuzatildi: saytdagi **"Telegram orqali kirish"** vidjeti `data-onauth` bilan ishlardi — Telegram skripti uni `eval` bilan chaqiradi, sayt CSP'si esa `eval`ni taqiqlaydi (bot sozlangach vidjet ko'rina boshladi va production'da kirish ishlamas edi) — vidjet `data-auth-url` rejimiga o'tkazildi: kirgach `/auth/telegram` sahifasiga qaytadi va ma'lumot (imzo bilan) backend'da tekshiriladi; o'qituvchi ro'yxatida `QuerySet` birlashmasi xatosi (`distinct` bilan) — ID lar orqali; sertifikatdagi LinkedIn havolasida sana brauzer va serverda turli vaqt zonasida hisoblanib, oy chegarasida hydration xatosi berishi mumkin edi — sana satrdan olinadi. Skrinshotlarda: PDF'da sertifikat ikkinchi varaqqa takrorlanardi (chop etishda `fixed` element har varaqda) — bitta A4 varaqqa cheklandi; QR ostidagi havola bo'linardi; 5 ta topshiriqli imtihonda hamma forma ochiq turib sahifa juda uzun edi — topshirilmaganlari ham yig'ildi (birinchisi ochiq). Sinov paytida landing testi bir marta vaqtdan oshdi (Docker VM'da boshqa loyiha konteynerlari CPU'ni band qilgan) — qayta ishga tushirilganda o'tdi.

### 7B.11. 16-qadam: XP, coin, kunlik topshiriqlar, shtraflar, reyting, referal mukofotlari

Qaror (2026-10-01): **ikki valyuta.** **XP** — reyting uchun, sarflanmaydi, shtraflar faqat XP'dan
(0 dan pastga tushmaydi). **Coin** — do'kon uchun: har topilgan XP bilan teng coin ham beriladi,
referal mukofotlari ham coinda; sovg'a olganda reyting tushmaydi.

**Qanday ishlaydi** (qiymatlar namunaviy, admin'da o'zgartiriladi)

1. **XP va coin:** dars tugatildi +10, dars testidan birinchi marta o'tildi +15, uy vazifasi
   topshirildi +20, offlaynda darsga vaqtida kelindi +10, oylik imtihondan o'tildi +50, kunlik 3
   topshiriq bajarildi — bonus +10. Faqat serverda tasdiqlangan harakatlar; bir harakat — bir marta.
2. **Kunlik topshiriqlar:** har kuni 09:00 da har bir faol o'quvchiga 3 ta — har kuni boshqacha,
   qayerga yetganiga qarab: keyingi darsni ko'rish, dars testidan o'tish, botda takrorlash (5
   savol), uy vazifasini topshirish, bugungi offlayn darsga vaqtida kelish. Botda va kabinetda;
   bajarilgani o'zi belgilanadi. Uchalasi — bonus va **seriya** (ketma-ket kunlar) davom etadi.
3. **Shtraflar (faqat XP):** kunlik topshiriqlar bajarilmadi −5 (kun oxirida), darsga sababsiz
   kelmadi −15, kechikdi −5, uy vazifasi muddatidan kechikdi −10. Test yiqilgani uchun shtraf yo'q.
   Har biri sababi bilan tarixda; o'qituvchi (o'z guruhi) yoki admin bekor qiladi.
4. **Kabinet:** XP, coin, seriya, bugungi topshiriqlar va tarix (botda XP ko'rsatilmaydi — faqat
   topshiriqlar).
5. **Reyting (saytda):** haftalik, oylik, umumiy; guruh va kurs bo'yicha; ism va familiyaning bosh
   harfi; eng yaxshi 10 ta va o'z o'rni; sozlamalarda "reytingda ko'rsatilmasin". Haftalik
   g'oliblarni kanalga e'lon qilish — admin'da yoqiladi (standart — o'chiq).
6. **Referal mukofotlari:** do'st telefonini tasdiqlab, birinchi darsni tugatsa — taklif qilganga
   +50 coin; do'st birinchi to'lovda 10% chegirma oladi (buyurtma summasidan, Click'dan oldin); do'st
   to'lasa — taklif qilganga +100 coin va **10% kupon** (keyingi to'lovga, bitta to'lovga bitta).
   14-qadamdan beri yozilgan takliflar ham hisoblanadi. O'zini taklif qilib bo'lmaydi.

**Backend:** `rewards` app — `Wallet` (XP, coin, seriya), `Ledger` (har o'zgarish sababi bilan,
bekor qilish), `GameSettings` (qiymatlar), `DailyTask`, `Coupon`; mavjud jarayonlarga ulash (dars,
test, vazifa, davomat, imtihon, to'lov, ro'yxatdan o'tish); beat (09:00 topshiriqlar, kun oxiri
shtraf, haftalik g'oliblar); API (hamyon, tarix, topshiriqlar, reyting, shtrafni bekor qilish);
to'lovda chegirma va kupon; bot: "✅ Bugungi topshiriqlar" va takrorlash testi; admin; testlar.

**Frontend:** kabinet "Yutuqlar" sahifasi (XP, coin, seriya, bugungi topshiriqlar, tarix), bosh
sahifada qisqa karta, reyting sahifasi, sozlamalarda "reytingda ko'rsatilmasin", to'lovda chegirma
va kupon, o'qituvchi sahifasida shtrafni bekor qilish; E2E.

### 7B.11a. 16-qadam natijalari (2026-10-01)

| Qism | Holat |
|---|---|
| Hamyon | Yangi `apps/rewards`: `Wallet` (XP, coin, seriya, "reytingda ko'rsatilmasin"), `Entry` (har o'zgarish sababi bilan; `key` bo'yicha bir marta; shtraf XP'ni 0 dan pastga tushirmaydi — aslida yechilgani saqlanadi va bekor qilinganda aynan shu qaytadi), `GameSettings` (barcha qiymatlar admin'da) |
| Mukofot va shtraf | O'qish hodisalaridan: dars tugatildi, test birinchi marta o'tildi, vazifa topshirildi (kechiksa — shtraf), imtihondan o'tildi, davomat (o'qituvchi saqlaganda: keldi — XP, kechikdi/kelmadi — shtraf; holat o'zgarsa oldingi yozuv bekor qilinib yangisi yoziladi, sababli — hech narsa). Mukofotdagi xato dars, test yoki vazifani hech qachon buzmaydi (alohida savepoint, log) |
| Kunlik topshiriqlar | 09:00 da faol o'quvchiga 3 ta: bugungi dars (bo'lsa — albatta), keyingi dars, ochiq test, uy vazifasi, botda takrorlash (Telegram ulangan va o'tilgan testlarda 5+ savol bo'lsa) — har kuni boshqacha tartibda. Bajarilgani hodisadan o'zi belgilanadi; uchalasi — bonus va seriya (topshiriq berilmagan kunlar seriyani uzmaydi); 00:10 da kechagisi bajarilmaganlarga shtraf va seriya uziladi. Telegram'i ulanganlarga ertalab botda ro'yxat |
| Bot | Menyuda **"✅ Bugungi topshiriqlar"** (va /today): har topshiriq yonida tugma (dars va vazifa — saytga parolsiz, test — botda, jadval); **takrorlash** — o'tilgan testlardan 5 savol, har javobdan keyin ✅/❌, oxirida natija va topshiriq bajarildi. XP va reyting botda ko'rsatilmaydi |
| Reyting | Hafta / oy / umumiy; kurs va guruh bo'yicha (o'quvchining o'zinikidan); eng yaxshi 10 ta (ism va familiyaning bosh harfi), o'z o'rni; yashirinlar ro'yxatda yo'q, o'zi o'z o'rnini ko'radi. Haftalik g'oliblar — dushanba 10:00 da kanalga (admin'da yoqilsa) |
| Referal | Do'st birinchi darsni tugatsa — taklif qilganga +50 coin; do'st birinchi to'lovda 10% chegirma (buyurtma summasi — Click'ka chegirmali); do'st to'lasa — +100 coin va 10% kupon (keyingi to'lovda o'zi qo'llanadi, bitta to'lovga bitta, to'langanda ishlatilgan). Taklif qilganga xabar (kabinet + Telegram) |
| Kabinet | **Yutuqlar** (XP, coin, seriya — bog'langan nuqtalar, bugungi topshiriqlar, taklif havolasi va kuponlar, tarix — "ko'proq", "qanday topiladi"), bosh sahifada qisqa karta, **Reyting**, sozlamalarda "Reytingda ko'rsatilmasin", kurs sahifasida chegirma (eski narx chizilgan) |
| O'qituvchi va admin | Guruh sahifasida oxirgi 30 kun shtraflari — sababi bilan bekor qilish. Admin: "XP va coin" bo'limi — sozlamalar, tarix (qo'lda qo'shish, istalgan yozuvni bekor qilish), hamyonlar, kunlik topshiriqlar, kuponlar. Menejer — tarix va kuponlar, qiymatlar — faqat admin |

Tekshiruv: backend **718 test** (yangi 46: hamyon — bir marta, 0 dan pastga tushmaslik, bekor qilish; hodisalardan mukofot va shtraf, davomat o'zgarishi; kunlik topshiriqlar — tanlash, bonus, seriya, kun oxiri shtrafi; reyting — davr, doira, yashirinlar; referal — coin, chegirma, kupon bir marta; API va o'qituvchining bekor qilishi; bot — bugungi topshiriqlar, takrorlash, ertalabki xabar; admin sahifalari), OpenAPI ogohlantirishsiz; frontend typecheck, eslint, **88 Vitest**; **52 ta E2E** (yangi 5: Yutuqlar, reyting, "reytingda ko'rsatilmasin", o'qituvchi shtrafni bekor qiladi, do'stga chegirma; axe).

Sinovda topilib tuzatildi: taklif qilganga boradigan xabar sarlavhasida coin soni uzatilmagan edi (xabar va mukofot yozilmay qolardi); chegirma API'si mehmonga 403 qaytarib, kurs sahifasida konsol xatosi berardi — endi har doim `{"discount": ...}`; OpenAPI'da sertifikat API'larining nomlari to'qnashardi (15-qadamdan qolgan).

### 7B.12. 17-qadam: coin do'koni

1. **Admin:** sovg'alar — nomi, rasmi, tavsifi, narxi (coin), turi (raqamli / jismoniy), zaxira
   (bo'sh — cheksiz), kimga (hamma / kattalar / SIFAT Kids), faol.
2. **O'quvchi (saytda):** "Do'kon" — sovg'alar, coin balansi; "Olish" → tasdiqlash → coin yechiladi
   (bir vaqtda ikki xarid bo'lsa ham balans manfiy bo'lmaydi, zaxira kamayadi) → "Buyurtmalarim".
3. **Topshirish:** menejerga xabar; admin'da holat: yangi → tayyor → topshirildi yoki bekor
   (coin qaytadi, zaxira tiklanadi); har holat o'zgarishida o'quvchiga xabar.

**Backend:** `shop` app — `Product`, `Purchase`; coin `rewards` hamyonidan; API (ro'yxat, olish,
buyurtmalarim); admin (holat amallari); testlar. **Frontend:** "Do'kon" va "Buyurtmalarim"
sahifalari, menyuda "Do'kon", E2E.

---

### 7B.12a. 17-qadam natijalari (2026-10-01)

| Qism | Holat |
|---|---|
| Sovg'alar | Yangi `apps/shop`: `Product` — nomi va tavsifi 3 tilda, rasm, narx (coin), turi (raqamli / jismoniy), zaxira (bo'sh — cheksiz), kimga (hamma / kattalar / SIFAT Kids), sotuvda, tartib. Zaxirasi tugagan sovg'a do'konda ko'rinmaydi |
| Olish | "Olish" → tasdiqlash → coin `rewards` hamyonidan yechiladi (tarixda "Do'kondan sovg'a"), zaxira kamayadi. Sovg'a qatori va hamyon qulflanadi: bir vaqtda ikki xarid bo'lsa ham balans manfiy bo'lmaydi va zaxiradan ortiq sotilmaydi; coin yetmasa — "Yana N coin kerak", hech narsa yozilmaydi. Narx va nom buyurtmada o'sha paytdagidek saqlanadi |
| Buyurtma | Holat: yangi → tayyor → topshirildi, yoki bekor (coin qaytadi — "Sovg'a bekor qilindi", zaxira tiklanadi). Yangi buyurtma — menejer va adminlarga xabar (kabinet + Telegram, havola admin'dagi buyurtmaga); har holat o'zgarishida o'quvchiga xabar (menejer izohi bilan) |
| Admin | "XP va coin → Do'kon: sovg'alar / buyurtmalar": buyurtma sahifasida **"Tayyor"** (izoh bilan), **"Topshirildi"**, **"Bekor qilish"** (sabab bilan) — faqat mumkin bo'lgan o'tishlar ko'rinadi. Menejer — sovg'alar va buyurtmalar; direktor — faqat ko'radi |
| Kabinet | Menyuda **"Do'kon"**: coin balansi, sovg'a kartochkalari (rasm yoki belgi, narx, qolgan soni), "Olish" yoki "Yana N coin kerak"; **Buyurtmalarim** — holat va izoh. Yutuqlar sahifasidagi coin kartasidan do'konga havola |

Tekshiruv: backend **731 test** (yangi 13: olish — coin va zaxira, coin yetmasa hech narsa yozilmaydi, tugagan va sotuvda bo'lmagan sovg'a, SIFAT Kids sovg'alari; holatlar, bekor qilishda coin va zaxira qaytishi, menejer va o'quvchiga xabarlar; API; admin amali va admin sahifalari); frontend typecheck, eslint, **88 Vitest**; **53 ta E2E** (yangi: o'quvchi sovg'a oladi — tasdiqlash, balans va zaxira kamayadi, qimmat sovg'a tugmasi o'chiq, Buyurtmalarim — "Yangi"; axe). Sertifikat PDF'i yakuniy build'da bitta A4 varaq (15-qadam tuzatishi tekshirildi).

Sinovda topilib tuzatildi: admin'dagi faqat ko'rish va amallar uchun sahifalarda (do'kon buyurtmasi, XP tarixi, hamyon, kunlik topshiriq, sertifikat) pastdagi "Saqlash" tugmalari chalg'itardi — olib tashlandi (o'zgarish faqat amallar orqali); kurs sahifasida chegirmali narx satri bo'linib ketardi — eski narx yangisining ustida; E2E artefaktlari (`test-results/`) eslint'ni buzardi — e'tiborsiz qoldirildi.

### 7B.12b. Botda admin panel va foydalanuvchilar statistikasi (2026-10-01, buyurtmachi so'rovi)

| Qism | Holat |
|---|---|
| Kim | Statistikani ko'rish huquqi borlar (direktor, admin, menejer) — Telegram'i akkauntiga ulangan bo'lsa. Ularning bot menyusida eng tepada **"📊 Admin panel"**; `/admin` buyrug'i ham (ochiq buyruqlar ro'yxatida yo'q). Boshqalarga (o'quvchi, o'qituvchi, ro'yxatdan o'tmagan) — "faqat administratorlar uchun", AI'ga yuborilmaydi |
| Panel | 👥 Foydalanuvchilar: bot — jami va yangi, ro'yxatdan o'tgan / o'tmagan, botni bloklagan, yangiliklarni o'chirgan; sayt o'quvchilari — jami va yangi, Telegram ulangan, SIFAT Kids. 📚 O'qish: tugatilgan darslar, o'tilgan testlar, o'qigan o'quvchilar, tekshiruv kutayotgan vazifalar. 💰 Savdo: kurs tanladi, to'ladi va tushum, arizalar (AI orqali), AI suhbatlar va xarajat. ⚠️ Muammolar (8 tagacha) yoki "Muammo yo'q". Oxirida "HH:MM holatiga" |
| Tugmalar | Bugun / Kecha / 7 kun / 30 kun va "🔄 Yangilash" — xabar joyida yangilanadi, huquq har bosishda qayta tekshiriladi; "🖥 Admin panel (sayt)" va (yuborish huquqi bo'lsa) "📣 Xabar yuborish" |
| Manba | Raqamlar `apps/stats/metrics` dan (admin bosh sahifasi bilan bir xil): yangi `audience` (bot va sayt foydalanuvchilari) va `learning`. Bo'lim nomlari 3 tilda; muammolar nomi — o'zbekcha (admin kabi) |
| Admin bosh sahifasi | Yangi karta **"Botga qo'shildi"** (davrda /start bosganlar; izohida jami, ro'yxatdan o'tmagan, bloklagan); "Ro'yxatdan o'tdi" kartasi izohida jami o'quvchilar |
| Taklif matni | Botdagi "Do'stni taklif qilish"da "mukofotlar tez orada" o'rniga amaldagi mukofotlar — o'yin sozlamalaridagi qiymatlar bilan (birinchi dars — coin; to'lov — coin va kupon; do'stga — chegirma; 0 bo'lsa qator chiqmaydi) |
| Havola tugmalari | Saytga olib boradigan tugmalar https domenda inline tugma; local'da (`http://localhost`) Telegram tugmani qabul qilmaydi — havola xabar oxirida matn (o'zgarmadi, 18-qadamda domen bilan tugma bo'ladi) |

Tekshiruv: yangi testlar — admin statistikani ko'radi va davrni almashtiradi (xabar joyida, raqamlar, tugmalar, https'da havola tugmalari), menejer menyusida tugma bor, o'quvchi va o'qituvchiga rad, akkauntsizga rad; taklif matni mukofotlari sozlamalardan; admin bosh sahifasida foydalanuvchilar va bot raqamlari.

### 7B.13. 18-qadam: ishga tushirish — batafsil vazifalar

**Qarorlar (2026-10-01):** kod GitHub'da ikki private repo'da (`sifatedu-backend`, `sifatedu-frontend`).
Fayllar va videolar **serverning o'zida** (SeaweedFS). Videolar 50 soatgacha bo'lgani uchun VPS:
**4 vCPU, 8 GB RAM, 160 GB NVMe, Ubuntu 24.04** (AHOST, Toshkent — TAS-IX orqali tez). Serverni
buyurtmachi **o'zi qo'llanma bo'yicha** sozlaydi (`docs/DEPLOY.md`), yangilash — **bitta buyruq**
(`infra/deploy/deploy.sh`). Shaxsiy ma'lumotlar va ularning zaxirasi O'zbekistondagi serverda
(shaxsga doir ma'lumotlar qonuni talabi).

| Qism | Vazifa |
|---|---|
| Server | `infra/deploy/setup-server.sh` (root, bir marta): yangilanishlar, Toshkent vaqti, swap 4 GB, Docker (rasmiy repo, log cheklovi, Docker Hub mirror), UFW (22/80/443), fail2ban, avtomatik xavfsizlik yangilanishlari, certbot. SSH kaliti qo'shilgan bo'lsa — parol bilan kirish o'chiriladi (kalit yo'q bo'lsa o'chirilmaydi: serverdan qulflanib qolmaslik uchun) |
| Kod | Ikkala repo GitHub **deploy key** (faqat o'qish) bilan: `/srv/sifatedu` va uning ichida `frontend/` |
| Sozlamalar | `infra/deploy/make-env.sh`: root, backend va frontend `.env`. Maxfiy qiymatlar serverda yaratiladi (`DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`, S3 kalitlari, `VIDEO_KEY_SECRET`, `TELEGRAM_WEBHOOK_SECRET`). Tashqi kalitlar (bot, Click, Eskiz, Anthropic, Google, Sentry) serverda so'raladi va chatga yozilmaydi. Mavjud `.env` ustidan yozmaydi |
| Domen va HTTPS | DNS: `sifatedu.uz`, `www`, `media` → server IP. Let's Encrypt (certbot, webroot, uchala nom uchun bitta sertifikat, `--cert-name sifatedu`), avtomatik yangilanadi va nginx qayta yuklanadi (`init-cert.sh`, `reload-nginx.sh`). `www` → asosiy domenga 301 |
| Fayllar | SeaweedFS production'da ham. `media.sifatedu.uz` — nginx orqali S3: imzolangan havolalar Host bilan tekshiriladi. Local sinovda imzoli GET/PUT — 200; imzosiz, noto'g'ri imzo, ro'yxat — 403; DELETE nginx'da yopiq; CORS preflight o'tadi. Disk hajmiga qarab avtomatik (`-volume.max=0`); bucket va CORS backend ishga tushganda (`ENSURE_BUCKETS`) |
| Yangilash | `infra/deploy/deploy.sh`: ikkala repo `git pull --ff-only` → build → `up -d` → tekshiruv (backend, frontend, https orqali sayt va API). Xato bo'lsa oldingi image'larga qaytadi. Migratsiyalar qaytmaydi — ular faqat qo'shiluvchi qilib yoziladi. Ishlatilmayotgan eski image'lar tozalanadi |
| Zaxira | PostgreSQL har kuni 03:00, 30 kun (bor) — serverdagi `backups/`. Haftada bir marta kompyuterga `scp` bilan nusxa (qo'llanmada). AHOST'da snapshot xizmati bo'lsa — butun disk |
| Monitoring | Server resurslari soatda bir tekshiriladi: disk 85% dan oshsa yoki bo'sh xotira 10% dan kam bo'lsa — Telegram ogohlantirish va admin "Muammolar"da. Tashqi uptime: UptimeRobot (bepul; `/healthz` va `/api/v1/health/`). Sentry (ixtiyoriy DSN). `status.sh`: konteynerlar, sertifikat muddati, bot webhook, oxirgi zaxira, disk |
| Integratsiyalar | Bot: `telegram_webhook set`, `bot_setup`, BotFather `/setdomain sifatedu.uz`. Local'da boshqa (test) bot tokeni kerak — bitta token webhook va polling'da bir vaqtda ishlamaydi. Click: kabinetda Prepare/Complete manzillari. Eskiz: SMS shablonlari. Google OAuth: domen. Anthropic: kredit |
| Tekshiruv | `manage.py check --deploy`; domen'da E2E smoke; Lighthouse (PageSpeed); 1000 so'mlik haqiqiy to'lov va qaytarish; SMS; bot (ro'yxatdan o'tish, test, admin panel, havola tugmalari); video yuklash va ko'rish; zaxiradan tiklash sinovi |
| Hujjat | `docs/DEPLOY.md` — qadam-baqadam qo'llanma (buyruqlar, kutilgan natija, muammo bo'lsa nima qilish) |

**Sizdan kerak:**
- VPS va uning IP manzili.
- Domen faollashuvi va DNS yozuvlari.
- Let's Encrypt uchun e-pochta.
- Click va Eskiz ma'lumotlari, Anthropic krediti.
- Ixtiyoriy: Sentry va UptimeRobot akkauntlari.

## 7D. Ishga tushgandan keyin: o'quvchi yig'ish va o'qitish (2026-10-03)

**Maqsad:** 1 oyda kamida 5 ta guruh (onlayn yoki offlayn). Onlayn darslar boshida Zoom orqali,
videolar keyin yuklanadi. Odamlar asosan Instagram'dan keladi.

**Qarorlar:**
- **Kupon:** daraja testida 70% va undan yuqori — 25%, aks holda 15%; 72 soat amal qiladi; har
  odamga bir marta; birinchi to'lovga. Bir nechta chegirma bo'lsa — eng kattasi (qo'shilmaydi).
- **AI maslahatchi:** Google Gemini, Claude olib tashlanadi. Samimiy gaplashadi; bilim bazasi va
  e'tirozlarga javoblar buyurtmachi bilan birga tuziladi. Kalit — Google AI Studio (pullik tarif:
  bepul tarifda yozishmalar o'qitishga ishlatilishi mumkin). Gemini ilovasi obunasi API bermaydi.
- **Kunlik test:** har kuni 07:00 → 23:00; kamida 20 savol guruhning o'tgan mavzularidan; o'quvchi
  darhol nechta to'g'ri va noto'g'ri ekanini ko'radi, to'g'ri javoblar va izohlar 23:00 dan keyin;
  jarima yo'q — XP va coin, guruhning kunlik va haftalik reytingi; o'qituvchi kim bajarmaganini
  ko'radi. Eski 09:00 dagi "3 ta topshiriq" o'rniga.
- **Onlayn guruhlar:** Zoom havolasi va jadval bilan; darslar o'qituvchi "Dars o'tildi" deganda
  ochiladi (offlayndagi kabi), videolar keyin.

### 19-qadam: yangi kelganlar yo'li

| Qism | Vazifa |
|---|---|
| Manba | `t.me/<bot>?start=ig` (yoki `tg`, `ads1` …): botga birinchi kirishda yoziladi, ro'yxatdan o'tganda akkauntga o'tadi. Admin va bot admin panelida manbalar bo'yicha statistika |
| Yo'nalish | Ro'yxatdan o'tgach (va kursga yozilmaganlar menyusida «🎯 Daraja testi») — faol daraja testi bor yo'nalishlar tugmalari |
| Daraja testi | Botda, vaqtli (standart 10–15 savol, 15 daqiqa), har javobda to'g'ri/noto'g'ri aytilmaydi; oxirida natija va daraja (boshlang'ich / o'rta / yaxshi). Savollar «Daraja testlari» xizmat kursida (o'quvchilarga ko'rinmaydi), admin'da tez kiritish bilan |
| Kupon | Birinchi tugatilgan testda: 70%+ → 25%, aks holda 15%, 72 soat. Kupon modeliga muddat va turi (taklif / daraja testi / qo'lda); chegirma — eng kattasi; muddati o'tgani qo'llanmaydi; kabinet va botda ko'rinadi |
| Ariza | Test tugashi bilan ariza (manba «Botdagi daraja testi»: yo'nalish, natija, kupon) — arizalar guruhiga, menejer qo'ng'iroq qiladi |
| Eslatmalar | 24 soatdan keyin — kupon va kurslar; muddat tugashiga 12 soat qolganda — oxirgi eslatma; kupon ishlatilgan yoki kursga yozilgan bo'lsa yuborilmaydi |
| Kontent | Python daraja testi savollari (men tayyorlayman); boshqa yo'nalishlar — keyin, buyurtmachi bilan |

**Natija (2026-10-03):**
- Yangi `placement` ilovasi: daraja testi (yo'nalish → xizmat kursidagi dars testi, savollar soni,
  vaqt), urinish va javoblar; admin'da «Sotuv → Daraja testlari / Daraja testi natijalari»
  (menejer ko'radi va sozlaydi).
- Kim ishlaydi: hali hech qaysi kursga yozilmaganlar (bosh admin — sinab ko'rish uchun). Kursda
  o'qiyotganlarga tugma ko'rinmaydi, eski tugma yoki menyu matni bilan ham test va kupon yo'q —
  aks holda keyingi oy to'loviga chegirma olib qo'yishardi.
- Testni tashlab ketganlar: vaqti tugagan test har 5 daqiqada yopiladi — natija, kupon, botga xabar
  va ariza (`placement-close-expired`); eslatmalar — har soatda (`placement-coupon-reminders`).
- Kupon modeliga `kind` (taklif / daraja testi / qo'lda) va `expires_at`; chegirma — eng kattasi
  (do'st chegirmasi yoki eng katta amal qiluvchi kupon), muddati o'tgani qo'llanmaydi. Kabinetdagi
  «Yutuqlar» sahifasi tepasida kupon chiptalari (turi, muddati, «Kursni tanlash»).
- Manba: `BotChat.source` → `User.signup_source`, do'st havolasi — `ref`; botdagi admin
  panelda «📍 Manbalar»; arizada `utm_source`.
- Python savollari — `backend/scripts/daraja_testi_python.py` (28 ta, har odamga 12 tasi,
  15 daqiqa). Testlar: `apps/placement/tests`, `apps/bot/tests/test_placement_bot.py`, kupon va
  chegirma — `apps/rewards/tests/test_referral.py`.

### 20-qadam: AI maslahatchi — Gemini

Claude (Anthropic SDK) o'rniga Google Gemini (`google-genai`): suhbat, vositalar (kurslarni
qidirish, ariza qoldirish, daraja testi va kupon taklifi), xarajat hisobi va oylik budjet, AI
sozlamalari admin'da, sinov to'plami (`assistant_eval`). Shaxsiyat — samimiy maslahatchi; bilim
bazasi (kurslar, narxlar, jadval, FAQ) va e'tirozlarga javoblar buyurtmachi materiallaridan.
Kalit bo'lmasa — oddiy (qoidaga asoslangan) javoblar, saytda chat yashirin.

**Natija (2026-10-03):**
- Anthropic SDK olib tashlandi, o'rniga `google-genai` (`generate_content` stream; Interactions
  API ham bor, lekin tarix bazada bizda — oddiy, to'liq qo'llab-quvvatlanadigan yo'l tanlandi).
  Model — `gemini-3.8-flash` (barqaror), fikrlash `low`; sozlamalar `GEMINI_*` (serverdagi eski
  `ASSISTANT_MODEL=claude-…` qatorlari endi o'qilmaydi).
- Tarix model-neytral bloklarda (`text`, `tool_use`, `tool_result`); Gemini 3 fikrlash imzolari
  (`signature`, base64) va chaqiruv ID si (`call_id`) saqlanib, keyingi so'rovda aynan qaytariladi —
  imzosiz vosita chaqiruvini Gemini 400 bilan rad etadi. Eski (Claude) suhbatlar ham davom etadi.
- Shaxsiyat: samimiy, odamdek; halol ishontirish va e'tirozlarga javob tartibi; bepul daraja testi
  va kupon bo'limi prompt'ga o'yin sozlamalari va faol testlardan o'zi yoziladi (saytdagi mijozga
  `t.me/<bot>?start=ai` — manba «ai»). Kurs qatorida sertifikat.
- Xarajat: keshdan o'qilgan tokenlar 10 foiz narxda, fikrlash — chiqish narxida; budjet aksiyasiz
  narxda (1.50 / 7.50).
- Bilim bazasi va e'tirozlar — buyurtmachi bilan: `docs/ai-maslahatchi.md` (savolnoma va javoblar
  qoralamasi). Kalit — Google AI Studio, pullik tarif.
- Testlar: `apps/assistant/tests/test_llm.py` (soxta SDK: contents, stream, imzolar, sozlamalar,
  to'xtash sabablari), agent va prompt testlari.

### 21-qadam: onlayn guruhlar Zoom orqali

Guruhga «darslar o'qituvchi belgilagach ochiladi» sozlamasi: offlayn — doim, onlayn — tanlov
(videosiz Zoom guruhlari uchun yoqiladi). Jadval, Zoom havolasi, eslatmalar, «Qo'shilish» va
davomat — mavjud; dars yozuvi havolasi kelmaganlarga.

**Natija (2026-10-03):** `StudyGroup.teacher_paced` («darslarni o'qituvchi ochadi», admin'da
guruh sahifasi va filtr). `apps/live/gates.paced_group` — offlayn yoki shu belgi yoqilgan onlayn
guruh: test va uy vazifalari o'qituvchi belgilagan darsgacha, testdan o'tish sharti (`quiz_gate`)
o'chadi, sertifikat shartida — o'tilgan darslar. Zoom havolasi guruhda (`meet_url`), qolgani —
13-qadamdagidek. Test: `apps/live/tests/test_covered.py::test_zoom_group_opens_lessons_by_the_teacher`.

### 22-qadam: guruhlarga kunlik test

Har kuni 07:00 da guruhdagi har o'quvchiga botda kamida 20 savol (guruhning o'tgan darslari
testlaridan, bir xil savol ketma-ket kunlarda takrorlanmasin), 23:00 da yopiladi. Natija
(to'g'ri / noto'g'ri soni) darhol; javoblar va izohlar 23:00 dan keyin. XP va coin, guruhning
kunlik va haftalik reytingi (botda va saytda), o'qituvchi sahifasida kim bajarmagani. Savollar
yetarli bo'lmasa (o'tgan darslarda 20 tadan kam) — test berilmaydi va o'qituvchiga eslatma.

**Natija (2026-10-03):**
- `apps/dailytest`: `DailyTest` (guruh va kun, OPEN / CLOSED / SKIPPED, 07:00–23:00),
  `DailyAttempt` (har o'quvchiga o'z savollari va aralashtirish kaliti), `DailyAnswer`. Beat:
  `daily-test-open` (07:00 va 07:30 — deploy paytida o'tib ketmasin), `daily-test-remind` (20:00),
  `daily-test-close` (har 15 daqiqa, vaqti o'tganlarni yopadi).
- Savollar banki — guruhda «Dars o'tildi» bo'lgan darslar testlari; har o'quvchiga tasodifiy,
  kechagilari iloji boricha qaytarilmaydi. Bank kichik bo'lsa — SKIPPED va o'qituvchiga haftada bir
  eslatma (`DAILY_TEST_TEACHER`).
- Botda (`apps/bot/daily.py`, holat `"k": "daily"`): ertalabki xabar tugmasi `dq`, «📝 Testlar»
  tepasida bugungi test, `?start=dt` havola; javobda baho yo'q, oxirida to'g'ri / noto'g'ri soni,
  XP va coin (`Entry.Reason.DAILY_TEST`, sozlamalar `GameSettings.daily_test_*`), guruhdagi o'rin;
  `dr` — kunlik va haftalik reyting, `dv` — xatolar, to'g'ri javob va izoh (faqat yopilgach).
- Sayt: `/dashboard/daily-test` (bugungi holat, reytinglar, tarix), `/dashboard/daily-test/[id]`
  (javoblar — yopilgach), menyuda «Kunlik test» (`me.in_group`); o'qituvchi guruh sahifasida kim
  ishladi va kim ishlamadi (`?daily=YYYY-MM-DD`).
- Test botda ham, saytda ham ishlanadi (2026-10-04, buyurtmachi so'rovi): urinish bitta —
  `POST /daily-test/{id}/start/`, `/attempts/{id}/answers/`, `/attempts/{id}/finish/`; saytda
  `QuizStep blind="daily"` (baho yo'q). Botda savolga saytda javob berilgan bo'lsa — bot keyingi
  savolga o'tadi. Baholash avtomatik (yozma javob — `grading.normalize` bilan aniq moslik).
- Testlar: `apps/dailytest/tests` (servislar, API), `apps/bot/tests/test_daily_bot.py`.

## 7C. Ko'p markazli platforma (SaaS) — qarorlar (2026-10-01)

**Buyurtmachi qarori (2026-10-03 yangilandi):** avval o'quvchi yig'ish va o'qitish (19–22-qadamlar, §7D), keyin 23–25-qadamlar.
Tizim boshqa **mustaqil o'quv markazlariga** (mijozlarga) oylik obuna
bilan beriladi. Har markazning o'z domeni, Telegram boti, Click hisobi va dizayni bo'ladi
(to'liq o'z brendi ostida). Tartib: 18-qadam (Sifat Edu ishga tushadi) → 19–21-qadamlar →
SIFAT Kids (boshidan ko'p markazli yoziladi). Talablar — TZ 4.22.

**Arxitektura tanlovi — har markaz uchun alohida PostgreSQL sxemasi (`django-tenants`):**

| Variant | Qaror | Sabab |
|---|---|---|
| Har markazga alohida server va nusxa | Yo'q | N ta server, deploy, zaxira va kuzatuv; yangilanish har biriga alohida |
| Bitta baza, har jadvalda `center_id` ustuni | Yo'q | 58 ta model va har bir so'rov o'zgaradi; bitta unutilgan filtr — boshqa markaz ma'lumoti ochiladi |
| **Har markazga alohida sxema** | **Ha** | Ajratish baza darajasida (so'rov boshqa markaz sxemasini ko'rmaydi), modellar deyarli o'zgarmaydi, bitta deploy |

**Hozirgi kodda nima o'zgaradi (o'lchab ko'rildi):** "Sifat" nomi 67 faylda to'g'ridan-to'g'ri
yozilgan (frontend 33, backend 34) — brend sozlamasiga o'tadi. Global bot tokeni (11 joy),
Click (6 joy), 3 ta yagona sozlama (AI, kontent, o'yin), fon vazifalari, kesh kalitlari va fayl
yo'llari markazga bog'lanadi. Frontend'dagi build paytida yoziladigan manzillar
(`NEXT_PUBLIC_APP_URL`, `NEXT_PUBLIC_S3_PUBLIC_URL`) so'rov paytida domen bo'yicha olinadi.
Markaz domenlari uchun HTTPS — talab bo'yicha avtomatik sertifikat (on-demand TLS).

**Pul va huquq:** har markaz o'quvchilardan o'z Click hisobiga oladi; platforma markazdan oylik
obuna oladi (shartnoma, bank o'tkazmasi). Boshqalarning pulini yig'ib bo'lib berish — yo'q
(litsenziya va soliq). Platforma — shaxsiy ma'lumotlarni qayta ishlovchi: har markaz bilan
shartnoma, server O'zbekistonda.

**Hozirgi ishlarga ta'siri:** 18-qadam o'zgarmaydi. Shu kundan yangi kodda "Sifat" nomi va
global sozlamalar to'g'ridan-to'g'ri yozilmaydi.

**19-qadam boshlanishidan oldin hal qilinadi:**
- platformaning nomi va domeni (mijozlarga sotiladigan mahsulot, super admin va subdomenlar uchun);
- tarif va narxlar;
- AI va SMS — markazning o'z kaliti bilan yoki platformaniki (budjet bilan).

## 8. Sizdan kerak bo'ladigan narsalar

Local ishlab chiqish uchun hech narsa kerak emas: SMS va to'lov test (dry-run) rejimida ishlaydi. Keyinroq kerak bo'ladi:

| Nima | Qachon |
|---|---|
| Logoning asl vektor fayli (SVG, AI yoki PDF), agar bor bo'lsa | 1-qadam |
| Telegram bot token va arizalar guruhi ID | 1-qadam (bo'lmasa, arizalar faqat admin'ga tushadi) |
| Landing matnlari, kurslar ro'yxati, ustozlar, narxlar | 1–3-qadamlar (hozircha namunaviy matn) |
| Eskiz.uz akkaunti | 2-qadam (production uchun) |
| Click merchant ma'lumotlari (`CLICK_SERVICE_ID`, `CLICK_MERCHANT_ID`, `CLICK_SECRET_KEY`), fiskalizatsiya hujjatlari va STIR | 5-qadam |
| Domen va O'zbekistondagi server | 6-qadam |
| ~~Anthropic API kaliti~~ ✅ berildi; **hisobni to'ldirish** (Anthropic Console → Plans & Billing) va oylik budjet | Hozir: kreditsiz AI oddiy rejimda javob beradi |
| ~~Telegram bot tokeni~~ ✅ berildi (@sifatedu_managerbot); arizalar guruhi ID (`TELEGRAM_LEADS_CHAT_ID`), xohlasangiz hisobot guruhi | Arizalar Telegram'ga tushishi uchun. Webhook — domen bilan |
| Eskiz akkaunti va SMS shablonlari (kod, to'lov, ommaviy xabar matnlari) | SMS haqiqatan yuborilishi uchun; hozir SMS test rejimida |
| ~~Kanal havolasi~~ ✅ berildi (yopiq kanal); **botni kanalga administrator qilish** (majburiy obuna) | Hozir |
| ~~Yangi bot tokeni~~ ✅ berildi (@sifat_edubot, menyu va tavsif yozildi); bot rasmi (BotFather); **yangi botni arizalar guruhiga qo'shish** | Hozir: arizalar guruhiga xabar eski bot o'rniga shu botdan boradi |
| XP, shtraf va referal qiymatlari (namunaviy qiymatlar bilan boshlanadi), coin sovg'alari ro'yxati | 16–17-qadamlar |
| Server va domen | 18-qadam (ishga tushirish) |

---

## 9. TZ o'zgarishlari

### v2.0 → v2.1 (ortiqcha qismlar olib tashlandi)

| Olib tashlandi | Sabab |
|---|---|
| Mavjud bo'lmagan `TZ.md` fayliga havolalar | O'rniga `PLAN.md` |
| Next.js Server Actions, Auth.js, "yagona Next.js ilova" | Backend alohida |
| Kubernetes, Meilisearch, Prometheus + Grafana, Video.js | Hozircha ortiqcha |
| 4-bosqichdagi noaniq funksiyalar: DRM, offline yuklab olish, bo'lib to'lash, kirill interfeysi, karyera markazi, vebinarlar | Qisqa "Backlog" ro'yxatiga o'tkazildi: mobil ilova, B2B, marketplace, blog |
| "Jamoa" bo'limi va tarixiy izohlar | Texnik talab emas |

### v2.1 → v2.2 (Python backend)

| O'zgarish | Sabab |
|---|---|
| NestJS, Prisma, BullMQ → **Django, DRF, Celery** | Buyurtmachi tanlovi |
| JWT → **Django session + CSRF**; `tokenVersion` → Django session auth hash | Bitta domen, mobil ilova yo'q: oddiyroq va xavfsizroq |
| 1-bosqich admin sahifalari frontend'dan olib tashlandi → **Django Admin (Unfold)** | Buyurtmachi tanlovi, ish hajmi kamayadi |
| Landing'dagi "Narxlar" bo'limi → **2-bosqich** | 1-bosqichda faqat bir martalik sotuv bor, narx kurs kartochkasida ko'rinadi. Alohida narxlar bo'limi obuna bilan kerak bo'ladi |
| JSON tarjima maydonlari → **django-modeltranslation** | Admin'da qulay |
| `UserRole` jadvali → **Django Group'lari** | Admin ruxsatlari bilan birga ishlaydi |
| `SiteContent` (key/value) → tuzilgan modellar (sozlamalar, FAQ, afzalliklar va h.k.) | Admin'da tahrirlash oson |
| `Instructor` profili 1-bosqichga o'tdi | Landing va kurs sahifasida ustoz 1-bosqichdayoq ko'rsatiladi |
| Frontend'dagi DOMPurify → **HTML faqat serverda tozalanadi (nh3)** | HTML bir joyda, saqlashda tozalanadi. SSR'da DOMPurify uchun jsdom kerak bo'lardi; foydalanuvchi matni esa umuman HTML sifatida chiqarilmaydi |
| Local storage: MinIO → **SeaweedFS** | MinIO Docker image'lari endi ochiq tarqatilmaydi. Production'da mahalliy S3 provayder ishlatiladi |

### v2.2 → v2.3 (landing redizayni, buyurtmachi fikri)

| O'zgarish | Sabab |
|---|---|
| Faqat qora tema → **kun va tun temalari** | Buyurtmachi talabi; odamlarning bir qismi yorug' fonni afzal ko'radi |
| 3D "SIFAT" hajmli logosi → **nuqtalardan yig'iladigan logo va ko'nikmalar turkumi**, kursor bilan ulanishlar | Birinchi variant "juda rasmiy" deb topildi; kursor bilan ulanish talab qilindi |
| Landing tartibi → **hikoya ko'rinishida**: xavotirlar, biz kimmiz (video), yo'l, kurslar + kasb testi, kafolatlar | Odamni "nega aynan biz" xulosasiga olib borish |
| Yangi kontent: xavotirlar, manifest, promo video | Admin'dan 3 tilda tahrirlanadi (TZ 4.1 talabi) |


### v2.3 → v2.4 (10-qadam: xabarnomalar va statistika)

| O'zgarish | Sabab |
|---|---|
| Email kanali olib tashlandi | Ro'yxatdan o'tish telefon orqali, email yig'ilmaydi. Telegram bepul va tezroq o'qiladi |
| "Har bir kanal va hodisani alohida o'chirish" → **Telegram xabarlarini o'chirish** va **aksiyalar roziligi** | Kam va tushunarli sozlama; to'lov va dars xabarlari baribir kerak |
| SMS — asosiy kanal emas, **Telegram'i yo'qlarga zaxira** | SMS pullik va har bir matn Eskiz'da shablon sifatida tasdiqlanishi kerak |
| "Bildirishnoma shablonlari" muharriri → avtomatik xabarlar matni kodda, 3 tilda | Xabarlar kam (4 ta), muharrir ortiqcha ish |
| Kunlik statistika 3-bosqichdan (4.19.1) **2-bosqichga** o'tdi; chuqur analitika (kogorta, retention) 3-bosqichda qoladi | Buyurtmachi talabi (11) |
| Faolsizlik eslatmalari (3 va 7 kun) 12-qadamga o'tdi | Testlar va o'yinlar bilan birga mazmunli eslatma bo'ladi |

### v2.4 → v2.5 (11-qadam: uy vazifalari)

| O'zgarish | Sabab |
|---|---|
| AI dastlabki review, o'xshashlik tekshiruvi (MOSS/JPlag), ZIP ichini ko'rish, ClamAV, audio/video izoh, rubrika, portfolio → **keyinroq** | Asosiy ehtiyoj — o'quvchi yuboradi, o'qituvchi tekshiradi. Qolganlari alohida katta ishlar |
| Faqat GitHub va ZIP → **izoh, kod, havola, istalgan ruxsat etilgan fayl va rasm** | Buyurtmachi talabi (1): fayl, kod yoki rasm; Kids uchun rasm va Scratch |
| Qayta topshirishlar soni cheklovi → **cheklovsiz, qabul qilinguncha** | Kam sozlama; o'qituvchi baribir har urinishni ko'radi |
| SLA 72 soat → admin statistikasida **48 soatdan oshgani muammo** sifatida | Kechikish darhol ko'rinadi |

### v2.5 → v2.6 (12-qadam: testlar va o'yinlar)

| O'zgarish | Sabab |
|---|---|
| Kod yozish va sandbox'da tekshirish (Judge0) → **keyinroq**; o'rniga "bu kod nima chiqaradi?" savollari | Sandbox — alohida server va xavfsizlik ishi; tushunishni tekshirish uchun kod o'qish yetarli |
| Moslashtirish va tartiblash 3-bosqichdan **hozirga** (o'yinli mashqlar) | Buyurtmachi talabi (7): test va o'yinlar |
| Vaqt chegarasi, urinishlar soni va kutish, yakuniy imtihon → **sertifikatlar bilan** | Dars testi — mashq: qayta urinish foydali, eng yaxshi natija hisobga olinadi |
| To'g'ri javobni qachon ko'rsatish sozlamasi → **har doim darhol** | O'yin tarzi: xato darhol tushuntiriladi |
| Katta-kichik harf sozlamasi, qisman ball → **olib tashlandi / keyinroq** | Kam sozlama |
| AI tushuntirishi, CSV/JSON import → **o'qituvchi izohi va matnli "Tez kiritish"** | AI hisobi hali ishlamayapti; matnli format o'qituvchiga qulayroq |
| 3 yulduz — faqat o'tilganda (o'tish bali 90% dan yuqori bo'lsa ham) | 2+ yulduz doim "o'tdi" degani bo'lsin |
| Faolsizlik eslatmasi ikki haftadan keyin yuborilmaydi | Matn aniq qolsin ("bir haftadan beri"), uzoq ketgan o'quvchi bezovta qilinmasin |

### v2.6 → v2.7 (yangi talablar: bot, imtihon, o'yinlar, referal, reyting)

| O'zgarish | Sabab |
|---|---|
| **Telegram bot + Mini App** (4.12.2, 14-qadam): saytdagi hamma funksiyalar botda, yangi yagona bot | Buyurtmachi talabi; tugmalar + Mini App — ikki marta yozmaslik uchun |
| Botda **majburiy kanal obunasi** (faqat botda, saytda emas) | Buyurtmachi talabi; saytda Telegram'siz foydalanuvchilar ham bor |
| Botda **SMS'siz ro'yxatdan o'tish** (Telegram kontakti) | SMS xarajati yo'q, tezroq |
| **Oila:** ota-ona va farzand profillari (14), **ota-ona rejimi** (4.12.3, 16) | Bolalar ota-ona telefonidan o'qiydi; tanlandi |
| **Oylik imtihon** 20 test + 5 amaliy (4.7.1, 15) — "yakuniy imtihon" o'rniga | Buyurtmachi talabi |
| **Sertifikat** B2 → 15-qadam; berish sharti oylik imtihonlarga bog'landi | Tanlandi |
| **Jonli darslar + davomat** (4.8.1, 13) | Davomat tanlandi |
| **XP, darajalar, nishonlar, reyting** B3 → 17-qadam; Kids ligasi | Buyurtmachi talabi (reyting) |
| **Referal (coin + chegirma)** — yangi (17) | Buyurtmachi talabi va qarori |
| **O'yinlar** (18) va **coin do'koni** (19) | Talablar (9, 10) va bolalarni jalb qilish |
| Payme, Uzum, to'liq promo-kod tizimi → **keyinroq** | Tanlanmadi; referal chegirmasi uchun minimal chegirma mexanizmi yetarli |
| Haftalik maqsad → **keyinroq** | Kunlik seriya yetarli, sozlama kam |

### v2.7 → v2.8 (muhokama davomi: video saytda, test botda, kunlik topshiriqlar)

| O'zgarish | Sabab |
|---|---|
| **Mini App olib tashlandi** — bot oddiy tugmalar bilan | Video faqat saytda; bot — ro'yxatdan o'tish, obuna, testlar, topshiriqlar, yangiliklar |
| **Dars testlari botda**, saytda zaxira; **70% va undan yuqori** bo'lsa keyingi dars ochiladi | Buyurtmachi talabi; javoblar urinish o'tilgach, savollar bankidan |
| **Offlayn: "Dars o'tildi"** — ustoz belgilagan dars ochiladi, test va vazifa chiqadi (13) | Buyurtmachi talabi |
| **Kunlik topshiriqlar va shtraflar** (16); XP faqat saytda | Buyurtmachi talabi; shtraf faqat XP, 0 dan past emas, test yiqilgani uchun yo'q |
| **Yangiliklar botdagi hammaga** (ro'yxatdan o'tmaganlarga ham) | Buyurtmachi talabi |
| Reyting — saytda | XP botda ko'rsatilmaydi |
| **SIFAT Kids, ota-ona rejimi, o'yinlar, Kids ligasi → oxirida** | Buyurtmachi: Kids uchun boshqa g'oyalar bor |
| Botda "oila" (farzand profillari) → Kids bilan oxirida | Kids keyinga qoldi |
| Tartib: 13 jonli darslar, 14 bot, 15 imtihon, 16 XP, 17 do'kon, 18 ishga tushirish | Yuqoridagilar |

### v2.8 → v2.9 (14-qadam: bot amalda)

| O'zgarish | Sabab |
|---|---|
| Obuna tekshiruvi 30 daqiqa eslab qolinadi; bot kanalda admin bo'lmasa — obuna so'ralmaydi, admin'ga ogohlantirish | Har xabarda Telegram'ga so'rov yubormaslik; o'quvchilar to'xtab qolmasin |
| To'g'ri javoblar va izohlar **saytda ham** test o'tilgach | Botdagi qoida bilan bir xil; qayta urinishda javobni yodlab o'tib ketmaslik |
| "Botdagi hammaga" — faqat filtrsiz xabarda | Bot foydalanuvchisining kursi va kabineti noma'lum |
| Botdan saytga — bir martalik parolsiz kirish havolasi (xodimga yo'q) | "Qayta kirish so'ralmaydi" talabi; xodim akkaunti himoyasi |
| Kunlik topshiriqlar menyusi — 16-qadam bilan | Topshiriqlar o'sha qadamda |

### v2.9 → v3.0 (15–17-qadamlar oldidan)

| O'zgarish | Sabab |
|---|---|
| Imtihon test qismi — saytda ham, botda ham (bitta urinish) | Buyurtmachi qarori |
| Imtihon qoralamasi har oy 20-kuni o'zi yaratiladi, o'qituvchi "Tayyor" qiladi | 5 ta amaliy topshiriq har oy yangi — ularni o'qituvchi yozadi |
| Sertifikat PDF'i — brauzer orqali (A4 sahifa, QR) | Serverga kutubxona o'rnatib bo'lmaydi (PyPI yopiq); natija bir xil |
| **XP va coin — ikki valyuta**; shtraf faqat XP'dan | Buyurtmachi qarori: sovg'a olganda reyting tushmasin |


### v3.0 → v3.1 (15–17-qadamlar amalda)

| O'zgarish | Sabab |
|---|---|
| Imtihon testida savolni keyinga qoldirish mumkin; topshirilmagan amaliy topshiriq formasi yig'ilgan (birinchisi ochiq) | 20 savol va 5 topshiriqda o'quvchi qotib qolmasin, sahifa haddan uzun bo'lmasin |
| Saytdagi "Telegram orqali kirish" — `data-auth-url` (qaytish sahifasi `/auth/telegram`) | `data-onauth` eval talab qiladi, sayt CSP'si buni taqiqlaydi |
| Seriya: topshiriq berilmagan kunlar seriyani uzmaydi | O'quvchiga topshiriq bo'lmagani uning aybi emas |
| Botda takrorlash topshirig'i faqat Telegram ulangan va o'tilgan testlarda 5+ savol bo'lsa | Bajarib bo'lmaydigan topshiriq berilmasin |
| Davomat XP'si va shtrafi o'qituvchi davomatni saqlaganda (o'zgarsa — qayta hisoblanadi) | "Qo'shilish" bosilgani hali kelgani emas; o'qituvchi tasdiqlaydi |
| Do'konda zaxirasi tugagan sovg'a ko'rinmaydi; buyurtmada nom va narx o'sha paytdagidek | Sotib bo'lmaydigan narsa chalg'itmasin; keyingi o'zgarishlar eski buyurtmaga ta'sir qilmasin |

### v3.1 → v3.2 (botda admin panel)

| O'zgarish | Sabab |
|---|---|
| Botda admin panel (`/admin`, "📊 Admin panel"): foydalanuvchilar, o'qish, savdo va muammolar statistikasi — direktor, admin, menejerga (4.12.2) | Buyurtmachi so'rovi: rahbarlar statistikani saytga kirmasdan ham ko'rsin |
| Admin bosh sahifasida bot foydalanuvchilari kartasi va jami o'quvchilar | Foydalanuvchilar statistikasi saytdagi admin panelda ham ko'rinsin |

### v3.2 → v3.3 (18-qadam: ishga tushirish)

| O'zgarish | Sabab |
|---|---|
| Bitta VPS (AHOST, Toshkent): ilova, baza, fayllar va zaxira bir serverda; alohida DB va object storage serverlari olib tashlandi | Boshlang'ich yuklama uchun yetarli, xarajat va boshqaruv sodda; kengayish yo'li TZ'da qoldi |
| Fayllar va videolar — serverdagi SeaweedFS (`media.<domen>`), mahalliy S3 provayder o'rniga | Buyurtmachi tanlovi: TAS-IX orqali tez, qo'shimcha to'lov yo'q, ma'lumotlar O'zbekistonda |
| Staging, image registry va avtomatik deploy olib tashlandi; o'rniga `deploy.sh` (tekshiruv va avtomatik qaytish bilan) | Bitta server va kichik jamoa; buyurtmachi qo'lda chiqarishni tanladi |
| Object storage versiyalash o'rniga — videolarning asl fayllari va provayder snapshot'i; baza nusxasi haftada bir serverdan tashqariga | SeaweedFS'da versiyalash yo'q; baza — eng muhim ma'lumot |
| Judge0 sandbox serveri boshlang'ich konfiguratsiyadan chiqarildi | Kod ishga tushirish funksiyasi rejada yo'q (kerak bo'lsa — alohida server) |
| Server resurslari kuzatuvi: disk va xotira → Telegram va admin "Muammolar" | Bitta serverda disk to'lsa baza va videolar yozilmay qoladi |

### v3.3 → v3.4 (ko'p markazli platforma)

| O'zgarish | Sabab |
|---|---|
| Yangi 4.22: platforma boshqa o'quv markazlariga obuna bilan beriladi; har markazning o'z domeni, boti, Click hisobi va dizayni | Buyurtmachi g'oyasi: har markazga alohida nusxa qilish o'rniga bitta tizim |
| Yo'l xaritasiga 19–21-qadamlar (ko'p markazli asos, brend va integratsiyalar, SaaS ishlatish); SIFAT Kids ulardan keyin | Kids boshidan ko'p markazli yozilsin, ikki marta ish qilinmasin |

### v3.4 → v3.5 (o'quvchi yig'ish: 19–22-qadamlar)

| O'zgarish | Sabab |
|---|---|
| Yangi kelganlar yo'li: manba havolalari, botda daraja testi, 15% / 25% kupon (72 soat, bir marta), menejerga ariza va eslatmalar | Buyurtmachi maqsadi: oyiga kamida 5 guruh, odamlar asosan Instagram'dan keladi |
| Kupon — muddat va turi bilan; bir nechta chegirma qo'shilmaydi, eng kattasi qo'llanadi | Chegirmalar tasodifan 40–50% ga yetib qolmasin |
| AI: Anthropic Claude → Google Gemini (Gemini 3.8 Flash, AI Studio pullik tarifi) | Buyurtmachi tanlovi; arzonroq. Bepul tarif yozishmalarni o'qitishga ishlatishi mumkin — pullik shart |
| Yo'l xaritasi: 19–22 — o'quvchi yig'ish va o'qitish (yangi kelganlar, Gemini, Zoom guruhlari, kunlik test); SaaS — 23–25 | Avval o'z markazini to'ldirish, keyin platformani sotish |
