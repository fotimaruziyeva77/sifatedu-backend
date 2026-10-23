# Kurslar rejasi: 1 oylik dasturlar, prezentatsiyalar va amaliy loyihalar

2026-10-23 · buyurtmachi so'rovi · **tasdiqlangan**: oyiga 12 dars, slaydlar saytda + PDF, yo'nalish ichida oylar. Slayd uslubi — buyurtmachining PDF namunalari (qora fon, SIFAT logotipi, kartalar).

Holat: **Python asoslari — tayyor** (12 dars, `backend/content/python/`); keyingisi — Frontend, 1-oy.

Maqsad — har bir yo'nalish uchun tayyor o'quv dasturi. Ustoz darsga tayyorlanmaydi: slaydni ochadi va
dars o'tadi. O'quvchi esa uyda shu slaydni ko'rib, test ishlaydi va uy vazifasini yuboradi. Hammasi
platformada turadi va har oy yangilanib boradi.

## 1. Har bir dars nimadan iborat («dars paketi»)

| Qism | Nima bo'ladi |
|---|---|
| **Slaydlar** | 15–25 ta: darsning maqsadi, nazariya, kod misollari, jonli namoyish bosqichlari, darsdagi mini-topshiriq, xulosa |
| **Ustozga eslatma** | 2 soatlik darsning vaqt rejasi (nazariya / amaliyot / tekshiruv), ko'p uchraydigan xatolar |
| **Test** | 12–15 savol («Tez kiritish» formati) — dars testi, kunlik test banki va oylik imtihon banki shu yerdan |
| **Uy vazifasi** | 3–5 ta amaliy topshiriq, har birida kutilgan natija (7-mavzudagi kabi — AI bilan tekshirsa bo'ladi) |

Har oy oxirida: **oylik imtihon** (test banki + 4–5 amaliy topshiriq) va **oy loyihasi** (amaliyot).

Sifat nazorati: testdagi va slayddagi barcha kod misollari avtomatik ishga tushirib tekshiriladi
(Python, JavaScript). Javobi xato savol tizimga tushmaydi. Til — o'zbek lotin, atamalar asl holicha
(`for`, `function`, `props`).

## 2. Prezentatsiyalar platformaga qanday joylashadi

**Tavsiya — slaydlar saytning o'zida** (yangi qadam, ~1 kun):

- Dars sahifasida «Slaydlar» bo'limi: ←/→ bilan varaqlash, proyektor uchun to'liq ekran, telefonda ham
  o'qiladi, «PDF yuklab olish» (brauzer orqali).
- Kontent repoda matn fayllari (`content/<kurs>/<NN-mavzu>.md`): slaydlar, test, uy vazifasi, ustoz
  eslatmasi. Serverda bitta buyruq (`import_course`) darslarni yaratadi yoki yangilaydi — qayta ishga
  tushirsa, ikki marta qo'shmaydi; mavjud darslar, test natijalari va guruhlarning «o'tilgan
  darslari» buzilmaydi.
- Afzalligi: fayl yuklash yo'q, slayd matni AI test tuzishga ham ishlaydi, xatoni bitta joyda tuzatsak —
  hamma guruhda yangilanadi.

Muqobillar: **PDF fayllar** (platformada o'zgarish yo'q, faqat yuklab olinadi; 130+ fayl repoga
tushadi) yoki **PowerPoint (PPTX) + PDF** (ustoz o'zi tahrirlay oladi, lekin fayllar og'ir va
yangilash qiyin).

## 3. Kurslar saytda qanday turadi

Tavsiya — mavjud yo'nalishlar ichida oylar (modullar). Oylik imtihon har oy o'sha oyning moduli bo'yicha
olinadi (imtihon tizimi buni allaqachon qo'llaydi).

| Kurs (saytda) | 1-oy | 2-oy | 3-oy | 4-oy | 5-oy |
|---|---|---|---|---|---|
| **Python** (hozirgi guruh) | Python asoslari | | | | |
| **Frontend** | HTML, CSS, Bootstrap, Tailwind | JavaScript | React | Next.js | Node.js |
| **Backend** | Python asoslari | Django | FastAPI | Telegram bot + AI | |
| **Sun'iy intellekt** | AI'dan foydalanish | | | | |
| **Kompyuter savodxonligi** | Kompyuter savodxonligi | | | | |
| **Praktikum Frontend / Backend** | amaliy loyihalar (§5) | | | | |
| **SIFAT Kids** | 12 oylik reja (§6) — hozircha faqat reja | | | | |

Bir oy = **12 dars** (haftasiga 3 marta, 2 soatdan) deb rejalashtirilgan. Boshqa jadval bo'lsa, darslar
soni o'zgaradi.

## 4. Oylik dasturlar (har biri 12 dars)

### Python asoslari

1–7-mavzular platformada bor (testlari bilan) — ularga slayd va uy vazifasi qo'shiladi. **Tayyor (2026-10-23):** `backend/content/python/01-python-asoslari/` — 12 dars, 228 slayd.

1. Python haqida, o'rnatish, `print()`, sintaktik xatolar, arifmetik amallar *(bor)*
2. O'zgaruvchilar, ma'lumot turlari, `input()`, turni o'zgartirish *(bor)*
3. String metodlari, f-string, kesimlar *(bor)*
4. `math` moduli va sonlar *(bor)*
5. Shartli, mantiqiy va taqqoslash operatorlari *(bor)*
6. Ro'yxat (`list`) bilan tanishuv *(bor)*
7. `list`, `tuple`, `dict`, `set` *(bor)*
8. `for` sikli va `range()`, ro'yxat ustida yurish
9. `while`, `break`, `continue`; «son topish» o'yini
10. Funksiyalar: `def`, parametrlar, `return`, standart qiymatlar, ko'rinish sohasi
11. Modullar (`random`, `datetime`), fayllar (`open`, `with`), xatolarni ushlash (`try/except`)
12. Yakuniy loyiha: konsol dastur («Do'kon kassasi» yoki «Kutubxona») va takrorlash

### Frontend, 1-oy: HTML, CSS, Bootstrap, Tailwind

1. Veb qanday ishlaydi; VS Code va Live Server; HTML tuzilmasi, matn, havola, rasm
2. Ro'yxatlar, jadvallar, semantik teglar (`header`, `nav`, `main`, `footer`)
3. Formalar: `input` turlari, `label`, `select`, `textarea`, tekshiruv atributlari
4. CSS asoslari: ulash usullari, selektorlar, ranglar, o'lchov birliklari, shriftlar
5. Box model: `margin`, `padding`, `border`, `display`, `box-sizing`
6. Flexbox: navbar va kartalar
7. Grid: sahifa tuzilmasi va galereya
8. Moslashuvchan dizayn: media query, mobile-first; `position`
9. Animatsiyalar: `transition`, `transform`, `@keyframes`; CSS o'zgaruvchilar
10. Bootstrap: grid tizimi, navbar, card, modal, utility klasslar
11. Tailwind CSS: utility-first, responsive prefikslar, hover va dark rejim
12. Yakuniy loyiha: landing sahifa va GitHub Pages'ga joylash

### Frontend, 2-oy: JavaScript

1. JS nima, brauzer konsoli; `let`/`const`, turlar, operatorlar
2. Matn va sonlar, template literal, `Math`, turni o'zgartirish
3. Shartlar: `if/else`, `switch`, ternar; truthy/falsy
4. Sikllar: `for`, `while`, `for...of`
5. Funksiyalar: oddiy va arrow, parametrlar, scope, callback
6. Massivlar: `push/pop/slice/splice`, `map/filter/reduce/find`
7. Obyektlar, destructuring, spread, JSON
8. DOM: elementni topish va o'zgartirish, element yaratish
9. Hodisalar: `click`, `input`, `submit`; formani tekshirish
10. `localStorage` + mini loyiha: To-do ro'yxat
11. Asinxron JS: `setTimeout`, Promise, `async/await`, `fetch`
12. Yakuniy loyiha: valyuta kursi ilovasi (Markaziy bank ochiq API'si)

### Frontend, 3-oy: React

1. React nima; Vite bilan loyiha; JSX va komponent
2. Props; ro'yxatni chiqarish (`map`, `key`)
3. `useState`, hodisalar, shartli ko'rsatish
4. Formalar (controlled input) va tekshiruv
5. `useEffect`; API'dan ma'lumot, yuklanish va xato holatlari
6. Holatni yuqoriga ko'tarish, `children`
7. React Router: sahifalar, dinamik yo'l
8. Stillar: Tailwind React'da
9. Context API va `useReducer` (savat misolida)
10. `useRef`, `useMemo`, o'z hooklarimiz
11. API bilan CRUD, `.env`, build va Vercel'ga joylash
12. Yakuniy loyiha: internet do'kon katalogi (filtr, savat, sahifalar)

### Frontend, 4-oy: Next.js

1. Next.js nima va nega kerak (SEO, SSR); App Router tuzilmasi
2. Sahifalar, layout, `Link`, dinamik yo'llar
3. Server va Client komponentlar
4. Serverda ma'lumot olish, kesh va qayta yangilash
5. `next/image`, `next/font`, Tailwind
6. Formalar va Server Actions
7. Route Handlers — o'z API'miz
8. Metadata va SEO, `loading`/`error` sahifalari
9. Ma'lumotlar bazasi: Prisma + PostgreSQL
10. Kirish va ro'yxatdan o'tish (Auth.js)
11. Vercel'ga joylash, muhit o'zgaruvchilari, domen
12. Yakuniy loyiha: e'lonlar sayti

### Frontend, 5-oy: Node.js

1. Node.js nima; modullar, npm
2. `fs`, `path`; fayl bilan ishlash, asinxronlik
3. `http` moduli bilan oddiy server
4. Express: routing, middleware
5. REST API: CRUD, status kodlar, Postman
6. Tekshiruv (zod) va xatolarni boshqarish
7. MongoDB va Mongoose
8. Autentifikatsiya: `bcrypt`, JWT
9. Fayl yuklash (`multer`), statik fayllar
10. Real vaqt: Socket.IO chat
11. Serverga joylash: PM2, `.env`, nginx
12. Yakuniy loyiha: React + Node API (to'liq stek)

### Backend, 2-oy: Django

1. OOP: `class`, obyekt, `__init__`, metodlar
2. OOP: meros, `super()`; `venv`, `pip`
3. Django: loyiha va ilova, MVT
4. URL, view, shablonlar
5. Modellar, migratsiyalar, ORM bilan CRUD
6. Admin panel
7. Formalar, ModelForm, CSRF
8. Statik va media fayllar, Bootstrap shablon
9. Foydalanuvchilar: ro'yxatdan o'tish, kirish, `login_required`
10. Django REST Framework: serializer, ViewSet, router
11. PostgreSQL, `.env`, gunicorn + nginx bilan joylash
12. Yakuniy loyiha: e'lonlar yoki blog sayti (CRUD + auth + admin)

### Backend, 3-oy: FastAPI

1. FastAPI va uvicorn; birinchi endpoint; Swagger
2. Path va query parametrlar, tip annotatsiyalar
3. Pydantic: request body, tekshiruv, response model
4. To'liq CRUD
5. SQLAlchemy + PostgreSQL
6. Alembic, loyiha tuzilmasi (routerlar)
7. Dependency Injection, sozlamalar (`.env`)
8. Autentifikatsiya: parol xeshi, JWT, OAuth2
9. Fayl yuklash, fon vazifalari
10. `async/await`, `httpx` bilan tashqi API
11. Testlar (`pytest`) va Docker
12. Yakuniy loyiha: vazifalar boshqaruvi API (auth + DB + testlar)

### Backend, 4-oy: Telegram bot + AI

Ikkala ma'noda: AI yordamida bot yozish (kodni AI bilan tushunish va tuzatish) va botga AI ulash.

1. Bot qanday ishlaydi; BotFather, token; aiogram 3; echo-bot
2. Komandalar, handler va filtrlar
3. Reply va inline tugmalar, callback
4. FSM: bosqichma-bosqich ariza
5. Baza: foydalanuvchilarni saqlash (SQLAlchemy async)
6. Admin funksiyalari: xabar tarqatish, statistika, middleware
7. Rasm, fayl va ovozli xabarlar
8. AI API (Gemini) ulash; kalitni yashirish; narx va limitlar
9. AI chat-bot: suhbat tarixi, system prompt
10. Foydali AI funksiyalar: tarjima, qisqartirish, rasmni tushunish
11. Webhook va serverga joylash (Docker)
12. Yakuniy loyiha: o'quv markazi uchun AI yordamchi bot (FAQ + ariza + AI javob)

### Sun'iy intellekt: AI'dan foydalanish

Dasturchi bo'lmaganlar uchun ham.

1. AI nima va qanday ishlaydi; ChatGPT, Gemini, Claude; xavfsiz foydalanish
2. Prompt yozish: rol, vazifa, ma'lumot, format
3. Matn: yozish, tahrirlash, tarjima, xat va rezyume
4. Hujjat va jadvallar: qisqartirish, tahlil (Excel/Sheets + AI)
5. Taqdimot va dizayn: AI bilan slayd, Canva
6. Rasm yaratish; mualliflik huquqi
7. Ovoz va video: matndan ovoz, subtitr, montaj
8. AI bilan o'qish: yangi mavzu, test, kartochkalar
9. Kod yozishda AI (boshlang'ich daraja)
10. Avtomatlashtirish: AI + Google Sheets / Telegram
11. Xavfsizlik va etika: deepfake, firibgarlik, faktni tekshirish
12. Yakuniy loyiha: AI yordamida shaxsiy loyiha va taqdimot

### Kompyuter savodxonligi

1. Kompyuter qurilmalari; Windows bilan tanishuv
2. Fayl va papkalar, arxiv
3. Klaviaturada tez yozish, qisqa tugmalar
4. Internet va brauzer: qidirish, yuklab olish, xavfsizlik
5. Elektron pochta va Google Drive
6. Word 1: matn va formatlash
7. Word 2: jadval, rasm, PDF; rezyume namunasi
8. Excel 1: jadval va formulalar
9. Excel 2: saralash, filtr, diagramma; oilaviy byudjet
10. PowerPoint: taqdimot
11. Xavfsizlik va davlat xizmatlari: parollar, firibgarlik, my.gov.uz, to'lov ilovalari
12. Yakuniy loyiha (Word + Excel + PowerPoint) va amaliy test

## 5. Amaliyot uchun loyihalar (Praktikum)

Har loyiha platformada alohida dars: maqsad, majburiy talablar, qo'shimcha (bonus), bosqichlar,
baholash mezonlari; topshirish — uy vazifasi orqali (GitHub havolasi).

**Frontend:** 1) shaxsiy portfolio · 2) restoran landing (Bootstrap) · 3) SaaS landing (Tailwind) ·
4) To-do (JS) · 5) valyuta kursi (API) · 6) viktorina o'yini · 7) kino katalogi (React + API) ·
8) internet do'kon (React, savat) · 9) blog (Next.js) · 10) e'lonlar sayti (Next.js + Node API)

**Backend:** 1) konsol kutubxona (Python) · 2) ariza qabul qiluvchi bot · 3) Django blog ·
4) Django do'kon (savat, admin) · 5) DRF API + JWT · 6) FastAPI vazifalar API ·
7) FastAPI + PostgreSQL + Docker · 8) AI chat-bot (Telegram + Gemini) · 9) to'lov integratsiyasi
(test rejimida) · 10) mini CRM o'quv markazi uchun

## 6. SIFAT Kids — 12 oylik reja (7–11 yosh, hozircha faqat reja)

| Oy | Mavzu | Oy yakunidagi ish |
|---|---|---|
| 1 | Kompyuter bilan do'stlashish: sichqoncha, klaviatura, xavfsiz internet | rasm va klaviatura o'yini |
| 2 | Algoritmik fikrlash: ketma-ketlik, takror (kompyutersiz mashqlar + Code.org) | labirint topshiriqlari |
| 3 | Scratch 1: qahramon, harakat, hodisalar | multfilm |
| 4 | Scratch 2: o'zgaruvchi va shartlar | labirint o'yini |
| 5 | Scratch 3: klonlar, ball, darajalar | arkada o'yini |
| 6 | Scratch 4: interaktiv hikoya va viktorina | yarim yillik ko'rgazma (ota-onalar uchun) |
| 7 | Dizayn: Canva, plakat, oddiy video montaj | plakat va qisqa video |
| 8 | 3D dizayn (Tinkercad) yoki Minecraft Education | 3D model / dunyo |
| 9 | Python Turtle 1: chizish, sikllar, ranglar (9–11 yosh) | naqsh va rasm |
| 10 | Python 2: matnli o'yinlar (son topish, viktorina) | o'z o'yini |
| 11 | Veb asoslari: HTML bilan «Mening sahifam» | shaxsiy sahifa |
| 12 | Yakuniy loyiha va bitiruv | o'yin yoki sayt taqdimoti, sertifikat |

7–8 va 9–11 yoshlar uchun topshiriqlar ikki darajada beriladi. Darslar ro'yxati keyingi bosqichda.

## 7. Bajarish tartibi

1. **Platforma:** saytda slaydlar va `import_course` buyrug'i (testlar, deploy).
2. **Python** — avval 8–12-darslar (hozirgi guruh 7-mavzuda; noyabr imtihonigacha kerak), keyin 1–7
   uchun slayd va uy vazifasi.
3. Frontend: HTML/CSS → JavaScript → React → Next.js → Node.js.
4. Backend: Django → FastAPI → Telegram bot + AI.
5. Sun'iy intellekt → Kompyuter savodxonligi.
6. Praktikum loyihalari.
7. SIFAT Kids: darsma-dars dastur (keyin).

Har oylik paket tayyor bo'lgach: siz 1–2 darsni ko'rib chiqasiz → tasdiqlaysiz → serverga import.
Birinchi paket (Python) ko'rib chiqilgandan keyin qolganlari shu andozada davom etadi.
