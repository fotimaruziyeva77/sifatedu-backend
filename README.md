# Sifat Edu

Online IT ta'lim platformasi. Loyiha ikkita mustaqil ilovadan iborat:

| Papka | Nima | Stek |
|---|---|---|
| [`backend/`](backend/) | REST API, admin panel, fon vazifalari | Python 3.13, Django 5.2 LTS, DRF, Celery |
| [`frontend/`](frontend/) | Sayt (3D landing, talaba kabineti) | Next.js 16, Tailwind v4, next-intl, React Three Fiber |

Bu root papka ularni Docker Compose orqali birga ishga tushiradi. Hujjatlar: [`docs/TZ-umumiy.md`](docs/TZ-umumiy.md) (texnik topshiriq) va [`docs/PLAN.md`](docs/PLAN.md) (ish rejasi).

**Ikki repozitoriy** (GitHub, private): **`sifatedu-backend`** — shu root papka (backend, Docker
Compose, nginx, zaxira, hujjatlar, CI) va **`sifatedu-frontend`** — `frontend/` papkasi. Frontend
repo backend repo ichiga `frontend/` bo'lib klonlanadi (root `.gitignore` uni e'tiborsiz qoldiradi),
shuning uchun compose fayllaridagi yo'llar o'zgarmaydi.

## Tez boshlash

Kerak: Docker Desktop va Git.

0. Ikkala repozitoriyni klonlang (frontend — backend ichiga):

   ```bash
   git clone https://github.com/fotimaruziyeva77/sifatedu-backend.git sifatedu
   cd sifatedu
   git clone https://github.com/fotimaruziyeva77/sifatedu-frontend.git frontend
   ```

1. `.env` fayllarini namunalardan yarating (birinchi marta):
   - `.env.example` → `.env`
   - `backend/.env.example` → `backend/.env`
   - `frontend/.env.example` → `frontend/.env`

   Parollar va `DJANGO_SECRET_KEY` uchun tasodifiy qiymat yozing.

2. Ishga tushiring:

   ```bash
   docker compose up --build
   ```

3. Namunaviy kontent (bo'sh bazada landing to'lishi uchun, ixtiyoriy):

   ```bash
   docker compose exec backend python manage.py seed_demo
   ```

   Faqat bo'sh jadvallarni to'ldiradi; keyin hammasi admin paneldan almashtiriladi.

4. Oching:

   | Manzil | Nima |
   |---|---|
   | http://localhost | Sayt |
   | http://localhost/admin/ | Admin panel (login: `backend/.env` dagi `DJANGO_SUPERUSER_*`) |
   | http://localhost/api/docs/ | API hujjati (Swagger) |
   | http://localhost:8888 | S3 fayl ko'ruvchisi (SeaweedFS) |

## Servislar

| Servis | Vazifasi |
|---|---|
| `nginx` | Yagona kirish nuqtasi: `/` → frontend; `/api/`, `/admin/`, `/static/` → backend |
| `frontend` | Next.js |
| `backend` | Django (API + admin) |
| `worker` | Celery: SMS, Telegram va boshqa fon vazifalari; `bulk` navbati — ommaviy xabarlar (SMS kodlari ularni kutmaydi) |
| `worker-ai` | Celery (`ai` navbati): AI maslahatchi javoblari, 8 ta oqimda (threads) |
| `worker-video` | Celery (`video` navbati): ffmpeg bilan HLS tayyorlaydi, bitta jarayonda |
| `beat` | Celery beat: davriy vazifalar |
| `postgres` | PostgreSQL 17 + pgvector |
| `redis` | Celery broker, kesh, sessiyalar |
| `seaweedfs` | S3-mos storage, production'da ham (bucket'larni backend avtomatik yaratadi) |

Local rejimda (`docker-compose.override.yml`) kod volume orqali ulanadi, o'zgarishlar avtomatik qayta yuklanadi. `node_modules` va Python muhiti faqat konteyner ichida saqlanadi.

Windows/macOS'da Docker volume fayl o'zgarishi haqida xabar bermaydi, shuning uchun local rejimda polling ishlatiladi:

- `frontend`: `next dev --webpack` + `WATCHPACK_POLLING` (Turbopack'ning polling'i bu muhitda ishlamadi). O'zgarish brauzerda 5–6 soniyada ko'rinadi. Production build odatdagidek Turbopack bilan yig'iladi.
- `worker`, `worker-ai` va `worker-video`: `watchfiles` kod o'zgarganda Celery'ni qayta ishga tushiradi, aks holda yangi vazifalarni tanimaydi.
- `backend`: Django `runserver` o'zi kuzatadi.

## Video darslar

Video admin panelda dars sahifasidagi **Video** maydoni orqali yuklanadi. Fayl brauzerdan
to'g'ridan-to'g'ri saqlovga ketadi (presigned multipart, 2 GB gacha) — Django orqali o'tmaydi.

Yuklash tugagach `worker-video` ffmpeg bilan ishlaydi: davomiylik, suratcha va HLS sifatlari
(360p/480p/720p/1080p, manba sifatidan oshmaydi). Segmentlar **AES-128** bilan shifrlanadi.

Himoya uch qatlamli:

1. Playlist har so'rovda qayta yasaladi, segment havolalari qisqa muddatli imzo bilan beriladi
   (`HLS_SIGNED_URL_TTL_SEC`).
2. Shifrlash kaliti `/api/v1/lessons/{id}/hls/key` orqali faqat kursga huquqi borlarga beriladi.
   Kalitning o'zi bazada `VIDEO_KEY_SECRET` bilan shifrlangan holda yotadi.
3. Pleyer ustida foydalanuvchi raqami bilan harakatlanuvchi belgi (watermark) ko'rinadi.

> Brauzer saqlovga o'zi murojaat qiladi, shuning uchun bucket'da CORS kerak. Uni
> `python manage.py ensure_buckets` o'rnatadi (`S3_CORS_ORIGINS`), konteyner ishga tushganda
> avtomatik chaqiriladi.

Kursga kirish huquqi `Kursga yozilishlar` bo'limidan qo'lda ham beriladi (to'lovlar 5-qadamda).
Onlayn — bir martalik to'lov, offlayn — oylik: `Amal qilish muddati` tugagach kirish yopiladi.

## To'lov (Click)

Kurs **onlayn** (bir martalik to'lov) yoki **offlayn** (oyma-oy) sotib olinadi. Summani
har doim backend hisoblaydi — brauzerdan kelgan qiymatga ishonilmaydi.

Tartib: `POST /api/v1/orders/` buyurtma yaratadi va Click sahifasiga havola beradi →
Click **Prepare** (`action=0`) va **Complete** (`action=1`) so'rovlarini yuboradi →
faqat muvaffaqiyatli Complete'dan keyin kurs ochiladi. Click sahifasidan qaytish
to'lovning isboti emas: `/payment/result` holatni backend'dan so'raydi.

Himoya:

| Talab | Qanday bajarilgan |
|---|---|
| Imzo | Har so'rovda MD5 (`sign_string`) tekshiriladi; Complete imzosiga `merchant_prepare_id` ham kiradi |
| Summa | Buyurtmadagi summa bilan solishtiriladi (Prepare'da ham, Complete'da ham) |
| Idempotentlik | `click_trans_id` unikal; takroriy Complete `-4` (Already paid) qaytaradi |
| Poyga | Buyurtma va tranzaksiya `select_for_update` bilan qulflanadi |
| Muddat | To'lanmagan buyurtma 30 daqiqada `EXPIRED` bo'ladi (Celery beat) |
| Log | Har bir so'rov va javob `To'lov loglari` bo'limida (imzo saqlanmaydi) |

Offlayn to'lovda `Enrollment.expires_at` to'langan oylar soniga uzayadi; muddat tugamasdan
to'lansa, yangi oylar ustiga qo'shiladi.

**Fiskal chek:** Click kalitlari va STIR berilmaguncha `FISCAL_DRY_RUN=true` — chek
ma'lumotlari logga yoziladi. Kursdagi `MXIK (IKPU) kodi` maydonini admin to'ldiradi.

**Pul qaytarish:** pul Click kabinetida qaytariladi, tizimda `Pul qaytarish` bo'limida
belgilanadi — shunda buyurtma `REFUNDED` bo'ladi va kursga kirish yopiladi.

> Click kalitlari bo'lmasa, kurs sahifasida sotib olish paneli o'rniga ariza formasi
> ko'rsatiladi.

## AI maslahatchi (24/7)

Saytdagi chat (kasb testi yonida va har sahifada pastki o'ng burchakda) va Telegram botda mijoz
savollariga kechayu kunduz javob beradi, mos kursni tavsiya qiladi va raqamini olib, **ariza**
yaratadi (Arizalar → manba: AI chat). Kurslar, narxlar, FAQ, "xavotirlar" va aloqa ma'lumotini
bazadan oladi — admin'da o'zgartirsangiz, AI ham darhol shuni aytadi.

**Ulash:**

1. [Google AI Studio](https://aistudio.google.com) → **Get API key** → kalit yarating. Loyihada
   **billing** (pullik tarif) yoqilsin: bepul tarifda yozishmalar Google mahsulotlarini
   yaxshilashga ishlatilishi mumkin, limitlari ham kichik.
2. `backend/.env`: `GEMINI_API_KEY=...`, `ASSISTANT_DRY_RUN=false`. Model — `GEMINI_MODEL`,
   narxi bilan birga o'zgartiriladi (1M token uchun, kiruvchi / chiquvchi):

   | Model | `GEMINI_MODEL` | Narx |
   |---|---|---|
   | Gemini 3.8 Flash (standart, barqaror) | `gemini-3.8-flash` | $1.50 / $7.50 (2026 yil oxirigacha $0.75 / $3.75) |
   | Gemini 3.1 Pro (kuchliroq, sinov holatida) | `gemini-3.1-pro-preview` | $2 / $12 |

   `GEMINI_THINKING_LEVEL=low` — fikrlash chuqurligi (chat uchun past: tez va arzon).
3. `docker compose up -d --force-recreate backend worker worker-ai`.
4. Admin → **AI yordamchi → AI sozlamalari**: kunlik va oylik budjet, "qo'shimcha ma'lumot"
   (chegirmalar, bo'lib to'lash, sertifikat, sinov darsi — AI faqat shu yerdagi va saytdagi
   faktlarni aytadi). E'tirozlarga javoblar — **Sayt kontenti → Xavotirlar**, savol-javoblar —
   **FAQ**. Daraja testi bo'lsa, AI uni va kuponni o'zi taklif qiladi.
5. Sifatni tekshirish (haqiqiy Gemini, ~$0,05–0,2): `docker compose exec backend python manage.py assistant_eval`.

**Kalitsiz (local):** `ASSISTANT_DRY_RUN=true` — chat "test rejimi" belgisi bilan ishlaydi: kurslarni
ko'rsatadi va raqam so'raydi, raqam yozilsa ariza yaratiladi. Budjet tugasa yoki Gemini ishlamasa
ham shu oddiy rejim ishlaydi — mijoz javobsiz qolmaydi.

**Xavfsizlik:** telefon raqamlari AI'ga yuborilmaydi (`‹telefon-1›` belgisi bilan almashtiriladi),
karta raqamlari saqlanmaydi, suhbatlar 90 kundan keyin anonimlashtiriladi. Suhbatlar admin'da:
**AI yordamchi → Suhbatlar** (transkript, 👎 baholar filtri, "Menejer kerak" holati).

**Telegram botda** AI maslahatchi — bot menyusidagi "💬 Savol berish": menyu tugmasi yoki test
javobi bo'lmagan har qanday matnga javob beradi (qarang: [Telegram bot](#telegram-bot)).

AI javoblari alohida `worker-ai` servisida tayyorlanadi (`ai` navbati): u band bo'lsa ham SMS kodlari
kechikmaydi.

## Kabinet

Kabinet ikki ko'rinishda ishlaydi va u foydalanuvchining `Kabinet ko'rinishi` maydoniga bog'liq:

| Qiymat | Kimga | Ko'rinishi |
|---|---|---|
| `ADULT` | 15 yoshdan kattalarga | Chapda menyu, sokin uslub, progress foizda |
| `KIDS` | SIFAT Kids o'quvchilariga | Robot-maskot, darslar "sarguzasht xaritasi"da (orol va toshlar), yulduz va medallar, kam matn |

Ko'rinishni o'quvchi (yoki ota-ona) **Sozlamalar → Kabinet ko'rinishi**da almashtiradi; admin'da
foydalanuvchi sahifasida ham bor.

* **Barcha kurslar** kabinet ichida ochiladi (`/dashboard/catalog`): menyu joyida qoladi, kurs
  ochiq bo'lsa "Sotib olish" o'rniga "Kursga o'tish" chiqadi.
* **Premium:** to'lab olingan kurs kabinetda oltin belgili — sarlavhada progress halqasi,
  darslar soni, umumiy soat, amal qilish muddati (offlayn) yoki "umrbod kirish" (onlayn).
  Kabinetda o'quvchi **o'zi sotib olgan shakl** ko'rsatiladi (kurs ikkala shaklda bo'lsa ham).
* **Dars materiallari:** admin'da dars sahifasining pastida — fayl (konspekt, taqdimot), havola
  yoki kod. Fayllar yopiq bucket'da, faqat darsga kirish huquqi bor o'quvchiga 2 soatlik
  imzolangan havola beriladi. Kodni o'quvchi nusxalaydi yoki fayl sifatida yuklab oladi.
* **Loader:** kabinetda bo'limlar orasida o'tishda kontent o'rnida brend loaderi; ommaviy sayt va
  kirish sahifalarida yuqorida ingichka chiziq. Saytda `loading.tsx` ataylab ishlatilmaydi: u
  javobni oqim bilan yuboradi va 404 sahifalar 200 holati bilan qaytib qoladi (SEO uchun yomon).

## Rollar

Beshta rol: **O'quvchi**, **O'qituvchi**, **Menejer**, **Direktor**, **Admin**. Kim nima qila
olishi kodda bitta jadvalda (`backend/apps/users/roles.py`) turadi va har `migrate`dan keyin
avtomatik qo'llanadi. Qo'lda qayta qo'llash: `python manage.py sync_roles`.

| Rol | Qayerda ishlaydi | Nima qiladi |
|---|---|---|
| O'quvchi | Kabinet | O'z kurslari, to'lovlari, sozlamalari |
| O'qituvchi | Kabinet → "Guruhlarim"; admin | O'z guruhlari va o'quvchilar progressi; o'z kurslariga modul, dars, material, video qo'shadi |
| Menejer | Admin | Arizalar, AI suhbatlar, o'quvchi akkaunti, kursga yozish, guruhlar; to'lovlarni ko'radi, pul qaytarish so'rovini ochadi |
| Direktor | Admin | Hamma narsani ko'radi, o'zgartirmaydi |
| Admin | Admin | Hammasi, jumladan rol berish, narxlar, sayt kontenti, AI sozlamalari |

**Rol berish:** admin → **Foydalanuvchilar** → foydalanuvchi → **Rollar** (faqat Admin ko'radi).
Xodim roli admin panelga kirishni o'zi beradi, roli olinsa — kirish yopiladi. Terminaldan:
`docker compose exec backend python manage.py grant_role +998901234567 TEACHER`
(`--remove` — olib tashlash).

**O'qituvchini sozlash:**
1. Foydalanuvchiga **O'qituvchi** roli.
2. **Katalog → Ustozlar** → ustoz profilida **Akkaunt** maydoniga shu foydalanuvchi; kurs sahifasida
   ustoz biriktirilgan bo'lsin — o'qituvchi admin'da faqat shu kurslarni ko'radi.
3. **O'qish → Guruhlar** → guruh ochish (kurs, o'qituvchi, jadval) va o'quvchilarni tanlash.
   O'qituvchi kabinetida "Guruhlarim" bo'limi paydo bo'ladi.

## Kunlik statistika va xabarnomalar

**Statistika** — admin bosh sahifasi (`/admin/`). Admin, Direktor va Menejer ko'radi; davr —
bugun, kecha, 7 yoki 30 kun (Toshkent vaqti):

- ro'yxatdan o'tganlar, kurs tanlaganlar, to'lovlar, arizalar va AI suhbatlar (oldingi davr bilan);
- voronka: ro'yxatdan o'tdi → kursga yozildi → to'lovni boshladi → to'ladi;
- **muammolar**: javobsiz arizalar, menejer kutayotgan AI suhbatlar, AI xatolari, kiritilmagan SMS
  kodlari, to'lov xatolari, video xatolari, yetkazilmagan xabarlar va tizim xatolari (har bir
  `ERROR` log bo'lim bo'yicha sanaladi, tafsiloti — Sentry'da);
- qo'ng'iroq qilish kerak bo'lganlar: kurs tanlamaganlar va offlayn to'lov muddati tugaganlar.

Har kuni soat 21:00 da (`DAILY_REPORT_HOUR`) direktor va adminlarga Telegram'da qisqa hisobot
boradi — ular kabinetda Telegram'ini ulagan bo'lsa. Guruhga ham kerak bo'lsa: `TELEGRAM_REPORTS_CHAT_ID`.

**Xabar yuborish** — admin → Xabarnomalar → Xabar yuborish (Admin va Menejer):

1. Sarlavha, matn va ixtiyoriy havola (Meet, kurs sahifasi yoki `/dashboard/...`).
2. Kimga: hamma, kattalar yoki SIFAT Kids; kurslar, guruhlar; faqat kurs tanlamaganlar; ro'yxatdan
   o'tgan sana oralig'i.
3. Kanallar: kabinet (har doim), Telegram (bepul), SMS (Telegram'i yo'qlarga; pullik va matn
   Eskiz'da shablon sifatida tasdiqlangan bo'lishi kerak).
4. **Saqlash** → **Menga sinov** → **Yuborish**. Oynada nechta odamga va qaysi kanal orqali
   borishi hamda SMS narxi ko'rinadi. Natija (yuborildi, yetmadi, o'qidi) shu sahifada.

"Aksiya va yangilik" turi Telegram va SMS orqali faqat rozilik berganlarga boradi (ro'yxatdan
o'tishda yoki sozlamalarda), kechasi (22:00–09:00) yuborilmaydi — ertalab 09:00 da ketadi.

**Avtomatik xabarlar**: to'lov qabul qilindi (Telegram bo'lmasa — SMS), admin kursni qo'lda
ochdi, offlayn to'lov muddatiga 3 kun qoldi va muddat tugadi (soat 10:00 da).

**Telegram'ni ulash** (o'quvchi): kabinet → Sozlamalar → Xabarnomalar → «Telegram'ni ulash» →
«Telegram'ni ochish» → botda «Start». Botda telefon yuborib ro'yxatdan o'tganlar va Telegram
orqali kirganlar avtomatik ulangan. Xabarlar [Telegram bot](#telegram-bot) orqali boradi (local
sinov — `telegram_poll`, production — `telegram_webhook set`).

## Uy vazifalari

1. **O'qituvchi vazifa beradi:** admin → Katalog → Darslar → dars → **"Uy vazifasi"** bloki
   (sarlavha, topshiriq, ixtiyoriy muddat). Har bir darsda bitta vazifa; o'qituvchi faqat o'z
   kurslari darslariga qo'sha oladi.
2. **O'quvchi javob yuboradi** dars sahifasida yoki kabinet → **Vazifalar** orqali: izoh, kod
   (tili bilan), havola (GitHub, sayt, Scratch) va 5 tagacha fayl yoki rasm (har biri 20 MB gacha,
   jami 50 MB). Tekshirilmagan javobni qaytarib olib, qayta yuborishi mumkin.
3. **Tekshirish:** kabinet → **Tekshirish** (O'qituvchi va Admin). Navbatda eng uzoq kutayotgani
   tepada, 48 soatdan oshgani qizil. Javob sahifasida kod, rasmlar, fayllar va oldingi urinishlar;
   qaror — **"Qabul qilish"** (baho 0–100 va izoh) yoki **"Qayta ishlashga qaytarish"** (izoh
   majburiy). Guruh ustozi o'z guruhi javoblarini, kurs ustozi — guruhsiz o'quvchilarnikini ko'radi.
4. **Xabarlar:** yangi javob — o'qituvchiga, natija — o'quvchiga (kabinet va Telegram).

Admin → O'qish → **Uy vazifalari** — barcha javoblar ro'yxati (faqat ko'rish). 48 soatdan beri
tekshirilmagan javoblar admin bosh sahifasida "muammo" sifatida chiqadi. Fayllar yopiq
storage'da turadi va hech qachon ishga tushirilmaydi; ruxsat etilgan turlar —
`backend/apps/homework/files.py`.

## Dars testlari va o'yinli mashqlar

1. **O'qituvchi test qo'shadi:** admin → Katalog → Darslar → dars → **"Test"** bloki (sarlavha,
   o'tish bali — standart 70%, har urinishda savollar soni — 0 bo'lsa hammasi, savollar tartibini
   aralashtirish). Saqlagach "o'zgartirish" havolasi yoki admin → **Testlar** test sahifasini
   ochadi. O'qituvchi faqat o'z kurslari testlarini ko'radi.
2. **Savollar** test sahifasidagi **"Tez kiritish"** maydoniga bir yo'la yoziladi. Xato bo'lsa,
   qator raqami bilan ko'rsatiladi; yangi savollar mavjudlarining oxiriga qo'shiladi. Savolni
   keyin alohida ham tahrirlash mumkin (variantlar turga qarab tekshiriladi).

````text
? HTML nimaning qisqartmasi?
+ HyperText Markup Language
- High Tech Modern Language
> HTML — sahifa tuzilmasi uchun belgilash tili.

? Qaysilari HTML teglari?
+ <div>
+ <p>
- <color>

? Eng katta sarlavha tegi qaysi?
= h1
= <h1>

? Brauzer sahifani qanday tayyorlaydi?
1. HTML o'qiladi
2. CSS qo'llanadi
3. JavaScript ishga tushadi

? Moslang:
HTML :: tuzilma
CSS :: ko'rinish

? Bu kod nima chiqaradi?
```js
console.log(2 + "2");
```
= 22
````

| Belgi | Ma'nosi |
|---|---|
| `?` | Yangi savol |
| `+` / `-` | To'g'ri / noto'g'ri variant (bir nechta `+` — bir nechta to'g'ri javob) |
| `=` | Matn javob; bir nechta qabul qilinadigan yozuv mumkin. Katta-kichik harf, ortiqcha bo'shliq va oxirgi tinish belgisi farq qilmaydi |
| `1.` `2.` … | Tartiblash (o'yin): qadamlar to'g'ri tartibda |
| `chap :: o'ng` | Moslashtirish (o'yin): juftlar |
| `>` | Izoh — javobdan keyin ko'rsatiladi |
| ` ``` ` | Savol ostidagi kod parchasi |

3. **O'quvchi** dars sahifasida "Testni boshlash"ni bosadi: savollar bittadan, har javobdan keyin
   darhol natija, to'g'ri javob va izoh, ketma-ket to'g'ri javoblar seriyasi. Yakunda foiz,
   yulduzlar (3 — o'tdi va 90%+, 2 — o'tdi, 1 — 50%+) va "Xatolar ustida ishlash". O'tsa — dars
   "tugatildi" deb belgilanadi. Qayta urinish cheklanmagan, eng yaxshi natija hisobga olinadi;
   to'xtatilgan test 24 soat ichida davom ettiriladi.
4. **Natijalar:** test sahifasida har savol bo'yicha to'g'ri javoblar foizi (qiyin savol
   ko'rinadi), admin → **Test natijalari**, kabinetdagi guruh sahifasida "Testlar" ustuni, kurs
   dasturida testli darslar yonida yulduzlar.

Baholash serverda: savollar brauzerga javobsiz boradi, variantlar esa baza ID si bilan emas,
shu urinishdagi o'rni bilan (`backend/apps/quizzes/services.py` → `Layout`).

**"O'qishga qaytish" eslatmasi:** har kuni 10:05 da kursni boshlagan, lekin 3–6 yoki 7–13 kundan
beri o'qimagan (dars ko'rmagan, vazifa yoki test yubormagan) o'quvchiga keyingi dars havolasi
ketadi — kabinet va Telegram, o'quvchi tilida, har tanaffusda har bosqich bir marta. Ikki haftadan
keyin yozilmaydi; kursni boshlamagan, tugatgan va muddati o'tganlarga ham.

## Jonli darslar va davomat

1. **Jadval:** admin → O'qish → Guruhlar → guruh → **"Haftalik jadval"** (hafta kuni, soat,
   davomiylik). Onlayn guruhga doimiy Meet/Zoom havolasi, offlayn guruhga xona yoziladi. Darslar
   14 kun oldinga har kecha (01:30) o'zi yaratiladi; jadval yoki havola o'zgarsa, kelgusi
   darslar moslanadi ("Jadvaldan darslarni yangilash" amali — darhol). Bitta darsni o'zgartirish
   yoki bekor qilish — admin → **Jonli darslar** yoki o'qituvchining dars sahifasida.
2. **O'quvchi:** kabinet → **Jadval** (menyuda — guruhi borlarga) va bosh sahifada "Keyingi jonli
   dars". Onlayn darsda **"Qo'shilish"** dars boshlanishidan 15 daqiqa oldin ochiladi: havola
   platforma orqali o'tadi (faqat guruh a'zolariga), bosilgani davomatga "Keldi" / "Kechikdi" bo'lib
   yoziladi. O'tgan darslar — davomat holati, o'qituvchi izohi va yozuv havolasi bilan.
3. **Eslatmalar** (kabinet va Telegram): dars kuni oldindan (24 soat ichida) va 30 daqiqa oldin;
   bekor qilinsa, yozuv qo'shilsa, darsga kelmasa (dars tugagach, 15 daqiqadan keyin — o'qituvchi
   xatosini tuzatishga ulgursin).
4. **O'qituvchi:** Guruhlarim → guruh → **Jonli darslar** → dars sahifasi: davomat (keldi, kechikdi,
   kelmadi, sababli; "Qolganlar — keldi" tugmasi), **"Dars o'tildi"**, izoh va yozuv havolasi,
   boshlanmagan darsni bekor qilish (sababi o'quvchilarga boradi). Guruh sahifasida har
   o'quvchining 30 kunlik davomati.
5. **"Dars o'tildi" (offlayn guruhlar):** o'qituvchi mavzuni (kurs darsini) tanlaydi — shu darsgacha
   test va uy vazifalari guruh o'quvchilariga ochiladi va ularga xabar boradi. Ustoz hali o'tmagan
   darsda o'quvchi "Test va uy vazifasi ustoz bu darsni guruhda o'tgach ochiladi" degan yozuvni
   ko'radi (video va materiallar ochiq). Menejer guruh sahifasidagi "O'tilgan darslar"da qo'lda ham
   belgilay oladi. Onlayn va guruhsiz o'quvchilarga bu cheklov yo'q.

Admin bosh sahifasida "Ketma-ket 2 marta darsga kelmagan o'quvchilar" muammosi chiqadi. Google Meet
API ishlatilmaydi — havola qo'lda qo'yiladi.

## Oylik imtihon va sertifikat

1. **Yoqish:** admin → kurs → **"Oylik imtihon"** (va "Sertifikat beriladi" — standart yoqilgan).
2. **Tayyorlash:** har oyning **20-kuni** shu oy imtihonining qoralamasi o'zi yaratiladi
   (oldingisining sozlamalari bilan; savollar — shu oy guruhlarda o'tilgan darslar modullaridan) va
   ustozlarga xabar boradi. Admin → **Oylik imtihonlar** → imtihon: 5 tagacha amaliy topshiriq,
   savollar modullari (bo'sh — butun kurs testlari), savollar soni, vaqt, o'tish bali, test ulushi
   → holat **"Tayyor"**. Topshiriq yoki savol bo'lmasa, imtihon qoralamada qoladi; ochilishiga
   5 kun qolganda tayyor bo'lmasa — admin bosh sahifasida ogohlantirish.
3. **O'quvchi:** 25-kundan oy oxirigacha — kabinet bosh sahifasida eslatma, **Imtihonlar**
   bo'limi, Telegram'da xabar. Test (saytda yoki botda "📝 Testlar"da) — bitta urinish, vaqt
   serverda (sahifa yopilsa ham ketadi, tugasa o'zi yakunlanadi), javob paytida to'g'ri/noto'g'ri
   aytilmaydi; foiz darhol, to'g'ri javoblar va izohlar imtihon yopilgach. Amaliy topshiriqlar —
   saytda (izoh, kod, havola, fayllar), baholanguncha yangilash mumkin.
4. **O'qituvchi:** Guruhlarim → **Oylik imtihonlar** → jadval (o'quvchi × topshiriq): katak bosilsa
   — javob va baho (0–100, izoh); kelolmagan o'quvchiga **alohida muddat** (yopilgandan keyin
   45 kungacha). Natija = test × ulush + amaliy o'rtachasi × qolgani; imtihon yopilib, hammasi
   baholangach — yakuniy, o'quvchiga xabar.
5. **Sertifikat** shartlar bajarilganda o'zi beriladi (har hodisadan keyin va har kecha 03:15 da
   tekshiriladi): barcha darslar (offlayn guruhda — guruhda o'tilgan), testli darslarning testi,
   qabul qilingan uy vazifalari, oylik imtihonlar o'rtachasi ≥ 60% (imtihon bo'lmasa — shart yo'q).
   Kabinet → **Sertifikatlar** (va qolgan shartlar). Ommaviy sahifa `/verify/<raqam>` — A4
   sertifikat, QR (shu sahifaga), "PDF yuklab olish" (brauzerning chop etish oynasi), Telegram va
   LinkedIn'ga ulashish. Admin → Sertifikatlar: **"Bekor qilish"** (sabab bilan — tekshirish
   sahifasida ko'rinadi) va "Qaytarish".

## XP, coin, kunlik topshiriqlar va reyting

* **Ikki valyuta:** XP — reyting uchun (sarflanmaydi, shtraflar faqat XP'dan va 0 dan pastga
  tushmaydi); coin — do'kon uchun (har topilgan XP bilan teng coin, referal mukofotlari ham
  coinda). Qiymatlar: admin → **XP va coin → Sozlamalar** (dars +10, test +15, vazifa +20, darsga
  vaqtida +10, imtihon +50, kunlik bonus +10; shtraflar: kunlik −5, kelmadi −15, kechikdi −5,
  vazifa kechikdi −10). Har o'zgarish sababi bilan **Tarix**da; bir harakat — bir marta.
* **Kunlik topshiriqlar:** har kuni 09:00 da faol o'quvchiga 3 ta (bugun darsi bo'lsa — albatta;
  qolganlari: keyingi dars, dars testi, uy vazifasi, botda takrorlash — har kuni boshqacha).
  Bajarilgani o'zi belgilanadi; uchalasi — bonus va seriya; bajarilmasa — 00:10 da shtraf va
  seriya uziladi. Telegram'i ulanganlarga ertalab botda ro'yxat; botda **"✅ Bugungi
  topshiriqlar"** va **takrorlash** (o'tilgan testlardan 5 savol, har javobdan keyin ✅/❌).
* **Kabinet:** **Yutuqlar** (XP, coin, seriya, bugungi topshiriqlar, taklif havolasi, kuponlar,
  tarix, "qanday topiladi"), bosh sahifada qisqa karta, **Reyting** (hafta / oy / umumiy; kurs va
  guruh bo'yicha; eng yaxshi 10 ta va o'z o'rni; ism va familiyaning bosh harfi). Sozlamalarda
  "Reytingda ko'rsatilmasin".
* **O'qituvchi:** guruh sahifasida oxirgi 30 kun shtraflari — sababi bilan bekor qiladi (XP
  qaytadi). Admin istalgan yozuvni bekor qiladi yoki qo'lda XP/coin qo'shadi.
* **Referal:** do'st havola orqali ro'yxatdan o'tib birinchi darsni tugatsa — taklif qilganga +50
  coin; do'st birinchi to'lovda 10% chegirma oladi (kurs sahifasida ko'rinadi, Click'ka chegirmali
  summa boradi); do'st to'lasa — taklif qilganga +100 coin va **10% kupon** (keyingi to'lovda o'zi
  qo'llanadi, bitta to'lovga bitta).
* **Haftalik g'oliblar:** admin'da yoqilsa, dushanba 10:00 da o'tgan haftaning eng faol 3
  o'quvchisi majburiy kanalga e'lon qilinadi (standart — o'chiq).

## Coin do'koni

1. **Sovg'alar:** admin → **XP va coin → Do'kon: sovg'alar** — nomi va tavsifi (3 tilda), rasm,
   narx (coin), turi (raqamli / jismoniy), zaxira (bo'sh — cheksiz), kimga (hamma / kattalar /
   SIFAT Kids), sotuvda yoki yo'q, tartib.
2. **O'quvchi:** kabinet → **Do'kon**: coin balansi, sovg'alar ("Olish" → tasdiqlash → coin
   yechiladi, zaxira kamayadi; coin yetmasa — "Yana N coin kerak"), **Buyurtmalarim** (holat va
   menejer izohi). Bir vaqtda ikki xarid bo'lsa ham balans manfiy bo'lmaydi va zaxiradan ortiq
   sotilmaydi.
3. **Menejer:** yangi buyurtma haqida xabar (kabinet + Telegram) → admin → **Do'kon: buyurtmalar**
   → buyurtma: **"Tayyor"** (izoh bilan, masalan, qayerdan olish), **"Topshirildi"** yoki **"Bekor
   qilish"** (sabab bilan — coin qaytadi, zaxira tiklanadi). Har o'zgarishda o'quvchiga xabar.

## Telegram bot

Bitta bot, oddiy tugmalar (Mini App yo'q). Video darslar — faqat saytda, qolgani botda ham:

* **Ro'yxatdan o'tish:** /start → til (bir marta) → majburiy kanalga obuna → **"📱 Telefonni
  yuborish"** — raqamni Telegram'ning o'zi tasdiqlaydi, SMS kerak emas. Raqam saytda bor bo'lsa,
  o'sha akkauntga ulanadi (bir raqam — bitta akkaunt). Xodim akkaunti kontakt orqali ulanmaydi —
  xodim Telegram'ni kabinetdagi "Telegram'ni ulash" bilan ulaydi.
* **Menyu:** 📚 Kurslarim (davom ettirish), 📝 Testlar, 📅 Jadval ("Qo'shilish"), 🎁 Do'stni taklif
  qilish, 💬 Savol berish (AI), ⚙️ Sozlamalar (til, yangiliklar, saytga kirish). Saytga olib
  boradigan tugmalar **parolsiz kiritadi** (bir martalik havola, 10 daqiqa) — faqat raqami
  Telegram orqali tasdiqlangan (kontakt yuborgan) chatga; xodimga hech qachon. Saytdagi havola
  bilan ulangan Telegram (masalan, umumiy kompyuterdagi birovniki) testlarni ishlay oladi, lekin
  saytga kira olmaydi — toki o'z raqamini yubormaguncha.
* **Dars testlari:** savollar tugmalar bilan (5 tur), har javobdan keyin faqat ✅/❌; o'tsa —
  xatolar, to'g'ri javoblar va izohlar, "Keyingi darsga"; o'tmasa — "Qayta urinish". Saytdagi test
  kartasida **"Telegram'da ishlash"** (asosiy) va "Saytda ishlash". Offlayn guruhda ustoz "Dars
  o'tildi" deganda botga **"Testni boshlash"** tugmali xabar keladi.
* **Onlayn o'quvchi:** keyingi dars oldingi testli darsning testidan (o'tish bali, standart 70%)
  o'tilgach ochiladi; yopiq darsda nima qilish kerakligi yoziladi. Bepul (preview) darslar,
  xodimlar va offlayn guruhlar bundan mustasno.
* **Yangiliklar:** admin → "Xabar yuborish"da **"Botdagi hammaga ham"** (filtrsiz xabar) va rasm —
  botga /start bosgan hammaga, ro'yxatdan o'tmaganlarga ham; kechasi yozilgani 09:00 da ketadi;
  har xabar ostida "🔕 Yangiliklarni o'chirish".
* **Do'stni taklif qilish:** shaxsiy havola — bot (`?start=r_KOD`) va sayt (`?ref=KOD`); kim taklif
  qilgani ro'yxatdan o'tishda yoziladi (admin → foydalanuvchi). Mukofotlar — 16-qadamda.
* **Yangi kelganlar:** manba havolasi (`?start=ig`, `?start=tg` …) ro'yxatdan o'tganda akkauntga
  yoziladi; hali kursga yozilmaganlarga **«🎯 Daraja testi»** — yo'nalish, vaqtli test, natija va
  daraja, chegirma kuponi (70%+ — 25%, aks holda 15%, 72 soat; bir marta) va menejerga ariza;
  kupon eslatmalari. Batafsil: [docs/yangi-kelganlar.md](docs/yangi-kelganlar.md).

**Ulash:**

1. [@BotFather](https://t.me/BotFather) → yangi bot: token va nomini `backend/.env` ga
   (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`), rasmini BotFather'da qo'ying. So'ng
   `docker compose up -d --force-recreate backend worker worker-ai beat`.
2. Buyruqlar menyusi va tavsif (3 tilda): `docker compose exec backend python manage.py bot_setup`.
3. Majburiy kanal: botni kanalga **administrator** qiling (bot ishlab turgan bo'lsin — webhook
   yoki `telegram_poll`) va admin → **Telegram bot → Majburiy kanallar** ga qo'shing: `@kanal`
   yoki yopiq kanal ID si `-100…` — bot administrator qilingan kanallar ID si bilan shu formada
   ko'rsatiladi. Bot a'zolikni tekshira olmasa, obuna so'ralmaydi va admin bosh sahifasida
   ogohlantirish chiqadi.
4. Arizalar guruhiga (`TELEGRAM_LEADS_CHAT_ID`) yangi botni qo'shing — xabarnomalar shu bot orqali.
5. Production: `TELEGRAM_WEBHOOK_SECRET=<tasodifiy qator>`, so'ng
   `docker compose exec backend python manage.py telegram_webhook set` (faqat https domen).
   Local sinov (domensiz): `docker compose exec backend python manage.py telegram_poll`.

Admin: **Telegram bot → Bot foydalanuvchilari** (kim /start bosgan, ro'yxatdan o'tganmi, til,
yangiliklar, bloklaganmi — faqat ko'rish). Guruhlardagi xabarlarga bot javob bermaydi.

**Botdagi admin panel.** Direktor, admin va menejerda (statistikani ko'rish huquqi) — Telegram'i
akkauntiga ulangan bo'lsa (kabinet → Sozlamalar → «Telegram'ni ulash») — bot menyusining tepasida
**«📊 Admin panel»** tugmasi bor (yoki `/admin` buyrug'i). Unda: bot foydalanuvchilari (jami,
yangi, ro'yxatdan o'tgan va o'tmagan, botni bloklagan, yangiliklarni o'chirgan), sayt o'quvchilari
(jami, yangi, Telegram ulangan, Kids), o'qish (tugatilgan darslar, o'tilgan testlar, tekshiruv
kutayotgan vazifalar), savdo (kurs tanladi, to'ladi, tushum, arizalar, AI) va muammolar. Davr
tugmalari — Bugun / Kecha / 7 kun / 30 kun — xabarni joyida yangilaydi. Raqamlar admin bosh
sahifasidagi bilan bir xil manbadan. Boshqalarga `/admin` — «faqat administratorlar uchun».

Botdagi saytga olib boradigan tugmalar (darsni ochish, saytga kirish, admin panel) faqat **https**
domenda tugma bo'lib chiqadi. Local muhitda manzil `http://localhost` — Telegram bunday tugmani
qabul qilmaydi, shuning uchun havola xabar oxiriga matn bo'lib yoziladi.

## Kirish va ro'yxatdan o'tish

Uch yo'l bor: **Google**, **Telegram** va **telefon + parol**. Google va Telegram bepul,
telefon yo'li esa SMS talab qiladi.

**Google** (bepul, 5 daqiqa):

1. [Google Cloud Console](https://console.cloud.google.com/apis/credentials) → **Create credentials** → **OAuth client ID** → **Web application**.
2. "Authorized JavaScript origins" ga sayt manzilini qo'shing: local uchun `http://localhost`, keyin haqiqiy domen.
3. Olingan Client ID ni `backend/.env` ga yozing: `GOOGLE_CLIENT_ID=...`.

**Telegram** (bepul):

1. [@BotFather](https://t.me/BotFather) da bot yarating (yoki arizalar uchun ishlatayotgan botni oling).
2. `/setdomain` buyrug'i bilan sayt domenini bog'lang. **`localhost` qabul qilinmaydi**, shuning uchun Telegram tugmasi faqat haqiqiy domenda ishlaydi.
3. `backend/.env` ga yozing: `TELEGRAM_BOT_USERNAME=bot_nomi` (@ siz) va `TELEGRAM_BOT_TOKEN=...`.

**SMS** (telefon + parol yo'li uchun): `backend/.env` da `SMS_DRY_RUN=true` bo'lsa, SMS
yuborilmaydi — kod worker logiga yoziladi (`docker compose logs worker`). Haqiqiy SMS uchun
[Eskiz.uz](https://eskiz.uz) hisobini oching va `ESKIZ_EMAIL`, `ESKIZ_PASSWORD` ni to'ldiring,
`SMS_DRY_RUN=false` qiling. SMS matni Eskiz'da oldindan tasdiqlanishi shart
(`apps/users/services.py` → `SMS_TEMPLATES`).

> `backend/.env` o'zgargandan so'ng `docker compose up -d --force-recreate backend` qiling:
> `restart` yangi qiymatlarni o'qimaydi.

Sozlanmagan provayder tugmasi saytda umuman ko'rinmaydi.

## Ariza xabarnomalari (Telegram)

Saytdagi "Bepul maslahat" arizasi admin panelga tushadi (Sotuv → Arizalar). Telegram guruhiga ham kelishi uchun `backend/.env` ga yozing:

```
TELEGRAM_BOT_TOKEN=...        # @BotFather bergan token
TELEGRAM_LEADS_CHAT_ID=...    # bot qo'shilgan guruh ID si (masalan, -100...)
```

So'ng `docker compose up -d backend worker`. Token bo'lmasa, ariza faqat admin panelda qoladi va logda shu haqda yoziladi.

## Foydali buyruqlar

```bash
# Backend: testlar, lint, tiplar
docker compose exec backend pytest
docker compose exec backend ruff check .
docker compose exec backend mypy .

# Backend: yangi migratsiya, namunaviy kontent
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py seed_demo

# Frontend: lint, tiplar, unit testlar, formatlash, API tiplarini yangilash
docker compose exec frontend npm run lint
docker compose exec frontend npm run typecheck
docker compose exec frontend npm test
docker compose exec frontend npm run format
docker compose exec frontend npm run gen:api

# Loglar
docker compose logs -f backend frontend
```

## Testlar va CI

| Qatlam | Vosita | Qayerda |
|---|---|---|
| Backend unit va integratsion | pytest (to'lov callback'lari, ruxsatlar, video, progress...) | `backend/apps/*/tests` |
| Frontend unit | Vitest (CSP, narx, `safeNext`, vaqt formati) | `frontend/src/**/*.test.ts` |
| E2E | Playwright: landing 3 tilda, katalog, **kirish → to'lov → kurs → dars**, kabinet sahifalari | `frontend/e2e` |
| Accessibility | axe-core (WCAG 2.1 A/AA) — har bir E2E sahifasida | `frontend/e2e/fixtures.ts` |

E2E har sahifada konsol xatolarini va **CSP buzilishlarini** ham ushlaydi. Ular production build
ustida ishlaydi — dev server sahifalarni so'rov paytida kompilyatsiya qiladi va sekin:

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.e2e.yml up -d --build frontend
docker compose exec backend python manage.py seed_e2e
cd frontend && npx playwright test -c e2e/playwright.config.ts
```

Batafsil: `frontend/e2e/README.md`. Dev server'ga qaytish: `docker compose up -d frontend`.

**CI** (GitHub Actions): backend repoda `.github/workflows/backend.yml` (ruff, mypy, migratsiyalar,
pytest, `check --deploy`) va `e2e.yml` (butun stack Docker'da + Playwright); frontend repoda
`.github/workflows/frontend.yml` (eslint, tsc, vitest, build). E2E frontend repoini ham yuklab oladi:
backend repo sozlamalarida secret **`FRONTEND_REPO_TOKEN`** (frontend repoga faqat o'qish huquqli
fine-grained token) va variable **`E2E_ENABLED=true`** qo'shilgach ishlaydi, ungacha o'tkazib
yuboriladi. Har bir PR yashil bo'lishi kerak.

## Xavfsizlik

- **CSP nonce bilan** (`frontend/src/proxy.ts`, `src/lib/csp.ts`): har so'rovda yangi nonce,
  `'strict-dynamic'`; tashqi manbalar — faqat Google/Telegram kirish, storage va Sentry.
  Qo'shimcha CDN manzili `CSP_EXTRA_ORIGINS` orqali qo'shiladi.
- nginx (production): TLS, HTTP → HTTPS, HSTS, `X-Content-Type-Options`, `Referrer-Policy`,
  `Permissions-Policy`, kirish endpointlariga IP limit, loglarda query yozilmaydi.
- Django: `python manage.py check --deploy` toza (CI'da tekshiriladi).
- Maxfiy qiymatlar image'ga kirmaydi (`.dockerignore`), faqat `.env` orqali.

## Monitoring

- **Sentry**: backend (Django + Celery) — `SENTRY_DSN` (`backend/.env`); brauzer —
  `SENTRY_DSN_FRONTEND` (root `.env`, image yig'ilganda yoziladi); frontend server xatolari —
  `SENTRY_DSN` (`frontend/.env`). Telefon raqamlari, cookie va so'rov tanasi yuborilmaydi.
- Loglar bir qatorli JSON (backend va frontend server xatolari).
- **Telegram ogohlantirishlari** (`TELEGRAM_ALERTS_CHAT_ID`): to'lov callback xatolari (imzo,
  summa, ichki xato), fiskal chek xatosi, video qayta ishlanmasligi. Bir xil ogohlantirish
  10 daqiqada bir martadan ko'p kelmaydi.
- Barcha servislarda `healthcheck`, jumladan `worker-video`, `beat` va `backup`.

## Production

To'liq qo'llanma — **[docs/DEPLOY.md](docs/DEPLOY.md)**: VPS'dan (AHOST, Ubuntu 24.04) to ishga
tushirishgacha har bir buyruq va kutilgan natija. Qisqasi:

| Qadam | Buyruq |
|---|---|
| Server (bir marta) | `bash infra/deploy/setup-server.sh` — Docker, firewall, swap, fail2ban, certbot |
| Sozlamalar | `bash infra/deploy/make-env.sh sifatedu.uz` — uchala `.env`, maxfiy qiymatlar serverda yaratiladi |
| Ishga tushirish va HTTPS | `bash infra/deploy/init-cert.sh <e-pochta>` — Let's Encrypt (`sifatedu.uz`, `www`, `media`) |
| Yangilash | `bash infra/deploy/deploy.sh` — yangilaydi, tekshiradi, xato bo'lsa oldingi versiyaga qaytadi |
| Holat | `bash infra/deploy/status.sh` |
| Umumiy server (boshqa loyihalar bilan) | `make-env.sh sifatedu.uz umumiy 8090` — Sifat nginx'i `127.0.0.1:8090` da, HTTPS serverdagi nginx'da (`infra/deploy/host-nginx.conf`, `certbot --nginx`) |

Fayllar va videolar serverning o'zida (SeaweedFS). Brauzer ularni `media.<domen>` orqali oladi:
nginx S3 API'ni imzolangan havolalar bilan o'tkazadi, o'chirish so'rovlari yopiq.
Production fayli: `docker-compose.prod.yml`.

**Backup:** `backup` servisi har kuni PostgreSQL nusxasini oladi (30 kun, ixtiyoriy S3'ga).
Tiklash tartibi: `infra/backup/README.md`.

## Portlar

Kompyuterdagi boshqa loyihalar bilan to'qnashmasligi uchun portlar root `.env` da sozlanadi: `HTTP_PORT` (sayt, standart 80), `POSTGRES_PORT` (15433), `S3_PORT` (9000), `S3_UI_PORT` (8888). Hammasi faqat `127.0.0.1` ga ochiladi.
