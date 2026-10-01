# SIFAT EDU — Online IT Ta'lim Platformasi

## Umumiy Texnik Topshiriq (TZ)

| | |
|---|---|
| **Hujjat turi** | Texnik topshiriq — butun loyiha |
| **Versiya** | 2.2 |
| **Sana** | 2026-09-26 |
| **Holat** | Tasdiqlash kutilmoqda |
| **Bog'liq hujjat** | `PLAN.md` — 1-bosqich (MVP) ish rejasi |

---

## Mundarija

1. Umumiy ma'lumot
2. Atamalar
3. Foydalanuvchi rollari va ruxsatlar
4. Funksional talablar
5. Sahifalar xaritasi
6. Texnik arxitektura
7. Ma'lumotlar bazasi modellari
8. API tuzilmasi
9. Tashqi integratsiyalar
10. Xavfsizlik
11. Huquqiy talablar
12. Nofunksional talablar
13. Infratuzilma va deploy
14. Sifatni ta'minlash va testlash
15. Rivojlantirish bosqichlari (yo'l xaritasi)
16. Qabul qilish mezonlari
17. Xavflar
18. Ochiq masalalar
19. Muhit o'zgaruvchilari

---

## 1. Umumiy ma'lumot

### 1.1. Loyiha haqida

**Sifat Edu** — O'zbekiston uchun online IT ta'lim platformasi. Platformada video darslar, har bir darsdan keyin testlar, amaliy loyihalar, AI yordamchi va sertifikatlar bor.

Platforma boshidanoq **hamma uchun, jumladan imkoniyati cheklangan shaxslar uchun** ham qulay bo'lishi uchun loyihalanadi. O'zbek imo-ishora tili (O'IT) va WCAG 2.1 AA talablari 3-bosqichda to'liq joriy qilinadi. Lekin arxitektura va komponentlar ularga birinchi kundan tayyorlab boriladi.

### 1.2. Maqsadlar

1. O'zbek, rus va ingliz tillarida sifatli IT kurslarini onlayn sotish va o'qitish.
2. O'quvchini kursni **oxirigacha yetkazish**: testlar, loyihalar, AI yordamchi, eslatmalar va gamifikatsiya orqali.
3. Imkoniyati cheklangan shaxslar uchun O'zbekistondagi birinchi to'liq moslashtirilgan IT ta'lim platformasini yaratish.
4. Bitiruvchilarni ish topishga tayyorlash: portfolio, sertifikat, hamkor kompaniyalar.

### 1.3. Maqsadli auditoriya

| Segment | Tavsif | Asosiy ehtiyoj |
|---|---|---|
| Boshlovchilar | 16–30 yosh, IT'ga kirmoqchi | Tushunarli yo'l, qo'llab-quvvatlash, ishga chiqish |
| Kasb almashtiruvchilar | 25–40 yosh, ishlaydi | Moslashuvchan jadval, amaliyot |
| Talabalar | OTM talabalari | Qo'shimcha ko'nikma, portfolio |
| Imkoniyati cheklangan shaxslar | Eshitish, ko'rish, harakat cheklovlari | O'IT, subtitlar, moslashtirilgan interfeys |
| Viloyatlardagi o'quvchilar | Sekin internet | Past sifatda uzluksiz video, offline rejim |

### 1.4. Raqobatdagi ustunliklar

- **O'IT integratsiyasi:** darslarda imo-ishora tili tarjimoni + IT atamalarining O'IT lug'ati (3-bosqich).
- **AI yordamchi:** dars mazmunini biladi, kodni tekshiradi, shaxsiy o'quv reja tuzadi.
- **Har bir darsdan keyin test**, har bir moduldan keyin amaliy loyiha.
- **Ko'p tillilik:** o'zbek, rus, ingliz — interfeys va kontent.
- **Mahalliy to'lovlar:** Click (keyinroq Payme va Uzum).
- **Sekin internetga moslashuv:** adaptive bitrate.
- **Zamonaviy 3D dizayn:** brendga mos, esda qoladigan landing (4.1.1-bo'lim).
- **Qo'llab-quvvatlash:** AI 24/7, jonli operator har kuni 09:00–23:00.

### 1.5. Biznes model

- Kursni **bir martalik** sotib olish (umrbod kirish).
- **Obuna** (oylik/yillik): barcha kurslarga yoki kurslar to'plamiga kirish (2-bosqich).
- **Promo-kodlar** va chegirmalar (2-bosqich).
- **Instruktorlar:** platforma xodimi yoki shartnoma asosida ishlaydi.

### 1.6. Muvaffaqiyat ko'rsatkichlari (KPI)

| Ko'rsatkich | 1-bosqichdan keyin | 1 yildan keyin |
|---|---|---|
| Landing → ro'yxatdan o'tish yoki ariza | ≥ 3% | ≥ 5% |
| Ro'yxatdan o'tgan → to'lov | ≥ 10% | ≥ 15% |
| Kursni tugatish darajasi | — | ≥ 40% |
| 30 kunlik retention (faol o'quvchilar) | — | ≥ 50% |
| NPS | — | ≥ 50 |
| To'lov xatolari (to'langan, lekin kurs ochilmagan) | 0 | 0 |

---

## 2. Atamalar

| Atama | Ma'nosi |
|---|---|
| **O'IT** | O'zbek imo-ishora tili |
| **PiP overlay** | Asosiy video ustida sahifa ichida joylashgan tarjimon videosi (brauzerning PiP API'si emas) |
| **Burn-in** | Tarjimon videosi asosiy videoga serverda "yopishtirilgan" yagona fayl |
| **HLS** | Videoni bo'laklab, turli sifatlarda yetkazish protokoli |
| **Enrollment** | Talabaning kursga kirish huquqi |
| **Lead** | Landing'dan qoldirilgan ariza |
| **RAG** | AI'ga javob berishda dars materiallarini kontekst sifatida berish usuli |
| **Sandbox** | Talaba kodini xavfsiz, izolyatsiya qilingan muhitda ishga tushirish |
| **MXIK (IKPU)** | Fiskal chek uchun mahsulot/xizmat identifikatsiya kodi |

---

## 3. Foydalanuvchi rollari va ruxsatlar

### 3.1. Rollar

| Rol | Kim | Asosiy vazifalari | Bosqich |
|---|---|---|---|
| **Mehmon** | Tizimga kirmagan tashrif buyuruvchi | Landing, katalog, preview darslar, AI maslahatchi, ariza | 1 |
| **O'quvchi** | Ro'yxatdan o'tgan foydalanuvchi | Kurs sotib olish, o'qish, test, uy vazifasi, AI | 1 |
| **Ota-ona** | O'quvchining (ko'pincha SIFAT Kids) ota-onasi | Farzand hisoboti, imtihon va davomat xabarlari | SIFAT Kids bilan, oxirida |
| **O'qituvchi** | Ustoz | O'z guruhlari va o'quvchilari, o'z kurslarining darslari va materiallari; uy vazifalarini tekshirish, jonli darslar va davomat, oylik imtihonning amaliy qismini baholash | 2 |
| **Menejer** | Sotuv va o'quv bo'limi | Arizalar, AI suhbatlar, o'quvchilarni kursga yozish va guruhlarga biriktirish, to'lovlarni ko'rish | 2 |
| **Direktor** | Rahbar | Hamma narsani ko'rish (o'zgartirmasdan), hisobotlar | 2 |
| **Admin** | Platforma egasi | Hamma narsa, rol berish | 1 |

Bitta foydalanuvchida bir nechta rol bo'lishi mumkin (masalan, O'qituvchi + Menejer). Xodim
rollari (O'qituvchi, Menejer, Direktor, Admin) boshqaruv paneliga kirish huquqini o'zi beradi.
"Support operator" roli olib tashlandi — murojaatlar va AI suhbatlar Menejerda (2-bosqich, 9-qadam).

### 3.2. Ruxsatlar matritsasi

Belgilar: **C** — yaratish, **R** — o'qish, **U** — tahrirlash, **D** — o'chirish, **own** — faqat
o'ziniki, **o'z kurslari** — kurs sahifasida ustoz sifatida biriktirilgan kurslar, **o'z guruhlari**
— unga biriktirilgan guruhlar.

| Resurs | Mehmon | O'quvchi | O'qituvchi | Menejer | Direktor | Admin |
|---|---|---|---|---|---|---|
| Landing, katalog, kurs sahifasi, preview dars | R | R | R | R | R | R |
| Pullik dars | — | R (sotib olgan) | R (o'z kurslari) | — | — | R |
| Kurs (narx, nashr) | — | — | R (o'z kurslari) | R | R | CRUD |
| Modul, dars, material, video | — | — | CRU (o'z kurslari) | R | R | CRUD |
| Guruhlar | — | — | R (o'z guruhlari) | CRU | R | CRUD |
| Kursga yozish (enrollment) | — | R (own) | — | CRU | R | CRUD |
| O'quvchilar progressi | — | R (own) | R (o'z guruhlari) | R | R | R |
| Ariza (lead), AI suhbatlar | C | C | — | CRU | R | CRUD |
| Buyurtma / to'lov | — | C, R (own) | — | R | R | R |
| Pul qaytarish | — | — | — | C, R | R | CRUD, tasdiqlash |
| Foydalanuvchilar | — | RU (own) | — | CRU (rolsiz) | R | CRUD, rol berish |
| AI sozlamalari (budjet) | — | — | — | R | R | CRUD |
| Sayt kontenti, sozlamalar | — | — | — | — | R | CRUD |
| Audit log | — | — | — | — | R | R |
| Test savollari (12-qadam) | — | — | CRUD (o'z kurslari) | R | R | CRUD |
| Test urinishlari (12-qadam) | — | C, R (own) | R (o'z guruhlari) | R | R | R |
| Uy vazifasi: topshiriq (11-qadam) | — | R (o'z kurslari) | CRUD (o'z kurslari) | R | R | CRUD |
| Uy vazifasi: javob va baho (11-qadam) | — | C, R (own) | R, baholash (o'z guruhlari va kurslari) | R | R | R, baholash |
| Sertifikat | R (tekshirish) | R (own) | R (o'z guruhlari) | R | R | CRUD, bekor qilish |
| Promo-kod | — | Qo'llash | — | CRUD | R | CRUD |
| Kunlik statistika va muammolar (admin bosh sahifasi) | — | — | — (o'z guruhlari progressi — kabinetda) | R | R, kunlik Telegram hisobot | R, kunlik Telegram hisobot |
| Ommaviy xabar (kabinet, Telegram, SMS) | — | R (own, kabinetda) | — | CRU, yuborish | R | CRUD, yuborish |

---

## 4. Funksional talablar

> Har bir bo'lim oxirida qaysi bosqichda amalga oshirilishi ko'rsatilgan: **[B1]** — 1-bosqich, **[B2]** — 2-bosqich va hokazo.

### 4.1. Landing page va ommaviy sahifalar [B1]

**Landing bo'limlari** (tartib — mijozni muammodan qarorgacha olib boradigan hikoya):
1. **Header:** logo, menyu, kun/tun tugmasi, til almashtirgich, "Kirish" va "Ro'yxatdan o'tish".
2. **Hero:** sarlavha, taklif, CTA'lar "Ro'yxatdan o'tish", "Bepul maslahat" va kasb testi; faqat haqiqiy raqamlar (kurslar, darslar, o'quvchilar).
3. **Xavotirlar:** o'quvchini to'xtatadigan xavotirlar va ularga javoblar.
4. **Biz kimmiz:** promo video (bo'lmasa motion-rolik), manifest, ustozlar.
5. **Qanday ishlaydi:** 4 qadam.
6. **Kurslar:** tavsiya etilgan kurslar kartochkalari va kasb testi (3 savol → mos kurs).
7. **Afzalliklar** (har bir kursda nima bor).
8. **Narxlar** **[B2]**: obuna rejalari paydo bo'lganda qo'shiladi. B1'da kurs narxi kurs kartochkasida ko'rinadi — onlayn (bir martalik) va offlayn (oylik) alohida.
9. **Fikrlar:** haqiqiy fikrlar bo'lmaguncha yashirin.
10. **Kafolatlar va FAQ.**
11. **Ariza formasi.**
12. **Footer:** kontaktlar, ijtimoiy tarmoqlar, huquqiy havolalar.

**Ariza (lead) formasi:**
- Maydonlar: ism, telefon (+998), qiziqqan kurs, izoh.
- Spamdan himoya: honeypot, rate limit, bitta raqamdan takroriy arizalar birlashtiriladi.
- Ariza DB'ga saqlanadi, Telegram guruhga va admin panelga (B2'dan Manager paneliga) yetkaziladi.
- UTM belgilari va manba sahifa saqlanadi.

**Umumiy talablar:**
- Barcha landing matnlari admin paneldan 3 tilda tahrirlanadi.
- SEO: `hreflang`, Open Graph, `sitemap.xml`, JSON-LD.
- Analitika hodisalari yuboriladi (14.4-bo'lim).

#### 4.1.1. Vizual uslub va 3D [B1]

- **Brend:** logodagi qizil (`#E31E24`) — asosiy aksent. Kun va tun temalari; tanlov saqlanadi, birinchi kirishda tizim sozlamasi olinadi. Logo SVG ko'rinishida qayta chiziladi.
- **Konsepsiya "Nuqtalarni bog'lang":** logo nuqtalardan yig'iladi, kursor yurgan joyda nuqtalar bir-biriga ulanadi, o'qish yo'li scroll bilan chiziladi.
- **Hero:** 3D "ko'nikmalar turkumi" — nuqtalardan yig'ilgan SIFAT logosi texnologiyalar grafigiga aylanadi, kursor yaqinidagi nuqtalar ulanadi. Sarlavha 3D bilan ustma-ust tushmaydi.
- **Boshqa bo'limlar:** 2D tarmoq foni, kurs kartochkalarida 3D tilt (CSS) va mini-animatsiyalar, scroll bilan chiziladigan yo'l, promo video yoki motion-rolik.
- **Dashboard, dars sahifasi va admin panelda WebGL 3D ishlatilmaydi** — faqat yengil animatsiyalar.
- **Tezlik:** LCP — HTML sarlavha va statik poster rasm. 3D sahna sahifa yuklangandan keyin lazy yuklanadi, bundle ≤ 250 KB (gzip). 12-bo'limdagi tezlik talablari 3D bilan ham bajarilishi shart.
- **Zaxira varianti:** `prefers-reduced-motion`, `Save-Data`, WebGL yo'qligi yoki kuchsiz qurilmada 3D o'rniga statik poster ko'rsatiladi. Mobil qurilmada soddalashtirilgan sahna.
- **Accessibility:** canvas `aria-hidden`, barcha mazmun DOM'da.

**Boshqa ommaviy sahifalar:**
- Platforma haqida.
- Ustozlar.
- Narxlar va obuna rejalari **[B2]**.
- Sertifikatni tekshirish **[B2]**.
- Accessibility sahifasi **[B3]**.
- Oferta, maxfiylik siyosati, refund qoidalari.
- Kontaktlar.

### 4.2. Autentifikatsiya va profil

**Kirish usullari:**
- Telefon raqami + SMS kod + parol **[B1]**.
- **Google orqali kirish [B1]** va **Telegram orqali kirish [B1]**: bir bosishda, SMSsiz. Ijtimoiy kirishdan so'ng telefon raqami bir marta so'raladi (menejer qo'ng'irog'i va to'lov uchun). Raqam band bo'lsa, SMS kod bilan mavjud akkauntga bog'lanadi.
- Email orqali kirish (ixtiyoriy, xorijiy foydalanuvchilar uchun) **[B2]**.

**Xavfsizlik va akkaunt:**
- Parolni SMS orqali tiklash **[B1]**.
- Admin, Instruktor va Manager uchun 2FA (TOTP) **[B2]**.
- Faol sessiyalar ro'yxati va "barcha qurilmalardan chiqish" **[B2]**.
- Akkauntni o'chirish so'rovi (shaxsiy ma'lumotlar qonuniga ko'ra) **[B2]**.

**Profil maydonlari:**
- Ism, familiya, rasm **[B1]**.
- Interfeys tili **[B1]**.
- Maqsad (masalan, "Frontend dasturchi bo'lish") **[B2]**.
- Haftalik o'quv soatlari maqsadi **[B2]**.
- Accessibility profili (ixtiyoriy va alohida rozilik bilan) **[B3]**.

**Ommaviy portfolio sahifasi** `/u/[username]`: tugatilgan kurslar, sertifikatlar, loyihalar. Foydalanuvchi o'zi yoqadi **[B2]**.

### 4.3. Kurslar katalogi va kurs sahifasi

**Kontent tuzilmasi** **[B1]**:
```
Kategoriya
└── Kurs
    └── Modul
        └── Dars
            ├── Video
            ├── Materiallar
            ├── Test [B2]
            └── (modul oxirida) Loyiha [B2]
```

**Katalog** **[B1]**:
- Filtrlar: kategoriya, kimga (kattalar / bolalar), o'qish shakli (onlayn / offlayn), bepul, daraja, til, narx.
- Filtrlar (O'IT mavjudligi bo'yicha) **[B3]**.
- Qidiruv, saralash (mashhur, yangi, narx).

**Kurs sahifasi:**
- Tavsif, treyler, dastur (syllabus), ustoz, narx (onlayn va offlayn alohida), davomiyligi, video tili **[B1]**.
- Kurs belgilari (badge): "Subtitr" va "O'IT tarjimon" **[B3]**.
- Sharhlar va reyting **[B2]**.
- "Bu kursdan keyin" — tavsiya etiladigan keyingi kurslar **[B2]**.
- O'quv yo'llari (Learning Path): kurslar ketma-ketligi, masalan "Frontend dasturchi: HTML → JS → React" **[B2]**.

**Kurs holatlari:**
- `DRAFT` → `PUBLISHED` → `ARCHIVED` **[B1]**.
- `DRAFT` → `IN_REVIEW` → `PUBLISHED` (instruktor kurslari admin tasdig'idan o'tadi) **[B2]**.

### 4.3.1. O'qish shakllari va narx **[B1]**

Bir kurs ikki shaklda o'qitilishi mumkin va narxlari boshqacha:

| Shakl | To'lov | Kirish |
|---|---|---|
| Onlayn | bir martalik | kurs ochiq qoladi |
| Offlayn | oyma-oy (abonement) | to'langan oy tugagach yopiladi (`Enrollment.expiresAt`) |

**Bepul kurslar:** `isFree` belgilangan kursni ro'yxatdan o'tgan har qanday foydalanuvchi
o'qiy oladi, to'lov talab qilinmaydi. Anonim foydalanuvchi faqat `isPreview` darslarni ko'radi.

### 4.4. O'quvchi paneli

Kabinet **ikki ko'rinishda** ishlaydi (`User.audience`) **[B1]**:

| Ko'rinish | Kimga | Qanday |
|---|---|---|
| `ADULT` | 15 yoshdan kattalarga | Chap tomonda menyu, sokin uslub, progress foizda |
| `KIDS` | SIFAT Kids o'quvchilariga (7–11 yosh) | Yirik rangli belgilar, progress yulduzlarda, kam matn |

Bo'limlar ikkalasida bir xil (asosiy, kurslarim, sozlamalar) — faqat ko'rinish va matn
uslubi boshqacha.

**Asosiy sahifa (Home):**
- "Davom ettirish" (oxirgi ko'rilgan dars) va kurslar progressi **[B1]**.
- Bugungi reja, haftalik maqsad va streak (ketma-ket o'qilgan kunlar) **[B2]**.
- AI tavsiyasi: "Keyingi eng mos qadam" **[B2]**.
- Muddati yaqinlashgan loyihalar va baholanmagan testlar **[B2]**.

**Mening kurslarim:**
- Progress (%) va "Davom ettirish" **[B1]**.
- Sertifikat olish tugmasi (kurs yakunlanganda) **[B2]**.

**Progress va statistika:**
- Haftalik va oylik o'quv soatlari grafigi (Recharts) **[B2]**.
- Test ballari va loyiha baholari **[B2]**.
- O'tilgan mavzular xaritasi (skill map) **[B3]**.

**Boshqa bo'limlar:**
- Buyurtmalar va to'lovlar tarixi **[B1]**.
- Sertifikatlar arxivi **[B2]**.
- Mening loyihalarim (portfolio) **[B2]**.
- Support ticketlar **[B3]**.
- Sozlamalar **[B1]**; accessibility sozlamalari **[B3]**.

### 4.5. Dars sahifasi va video pleyer

**Video pleyer** **[B1]**:
- HLS, sifat tanlash, tezlik (0.5x–2x), to'liq ekran.
- Klaviatura boshqaruvi.
- Oxirgi pozitsiyadan davom ettirish.

**Dars sahifasi** **[B1]**:
- Darslar ro'yxati (sidebar), materiallarni yuklab olish.
- "Oldingi" va "Keyingi" dars tugmalari.
- Progress avtomatik saqlanadi: dars ≥ 90% ko'rilsa, tugatilgan hisoblanadi.

**Qo'shimcha imkoniyatlar:**
- Dars ostida savol-javob: talabalar savol beradi, instruktor yoki boshqa talabalar javob beradi **[B2]**.
- O'ng panelda AI chat (dars kontekstida) **[B2]**.
- Shaxsiy qaydlar: vaqt belgisi bilan, video pozitsiyasiga bog'langan **[B2]**.
- Subtitlar (WebVTT, 3 til) **[B3]**.
- Matnli transkript (qidiruv mumkin, bosilganda videoning shu joyiga o'tadi) **[B3]**.
- O'IT tarjimon overlay (4.21-bo'lim) **[B3]**.

**Darslarning ochilish tartibi** **[B2]**:
- Instruktor kurs uchun tanlaydi: "barcha darslar ochiq" yoki "ketma-ket".
- Ketma-ket rejimda keyingi dars oldingi darsning testi o'tilgandan keyin ochiladi.

### 4.6. Video tizimi

**Yuklash va qayta ishlash** **[B1]**:
- Resumable multipart yuklash to'g'ridan-to'g'ri object storage'ga.
- Maksimal hajm 2 GB (sozlanadi).
- Fon worker'i (ffmpeg) videoni HLS'ga o'giradi: 360p / 480p / 720p / 1080p.
- Davomiylik va thumbnail avtomatik olinadi.
- Holatlar: `UPLOADING` → `PROCESSING` → `READY` / `FAILED`.

**Himoya** **[B1]**:
- Qisqa muddatli imzolangan URL'lar.
- HLS AES-128 shifrlash; kalit faqat ruxsati borlarga beriladi.
- Foydalanuvchi ID'siga asoslangan harakatlanuvchi watermark.

**Yetkazib berish:**
- Adaptive bitrate; 1.5 Mbit/s'da 480p uzluksiz **[B1]**.
- CDN yoki nginx kesh **[B1]**.

**Qo'shimcha:**
- Subtitlarni avtomatik yaratish (ASR) → instruktor yoki muharrir tahrirlaydi → nashr qilinadi **[B3]**.
- O'IT videolari alohida trek sifatida saqlanadi; burn-in versiyasi avtomatik yaratiladi **[B3]**.

**Texnik muammo haqida xabar** **[B3]**: pleyer xatosi (video yuklanmadi, 3+ marta buferlash) avtomatik log qilinadi. Foydalanuvchiga "Muammo haqida xabar berish" tugmasi taklif qilinadi va u ticket yaratadi.

### 4.7. Testlar va o'yinli mashqlar (2-bosqich, 12-qadam)

Maqsad — o'quvchi darsni tushunganini tekshirish (buyurtmachi talabi 7). Test darsga bog'lanadi;
modul testi — videosiz, faqat testli dars.

**Savol turlari** (hammasi avtomatik tekshiriladi, serverda):

| Tur | Izoh |
|---|---|
| Bitta to'g'ri javob | Ha/yo'q ham shu tur; savolga kod parchasi qo'shish mumkin ("bu kod nima chiqaradi?") |
| Bir nechta to'g'ri javob | Hammasi to'g'ri belgilansa — to'g'ri |
| Matn bilan javob | Ruxsat etilgan javoblar ro'yxati; katta-kichik harf va ortiqcha bo'shliq hisobga olinmaydi |
| Tartiblash (o'yin) | Qadamlarni to'g'ri tartibga qo'yish |
| Moslashtirish (o'yin) | Chap va o'ng ustunni juftlash |

**Sozlamalar:** o'tish bali (standart 70%), har urinishdagi savollar soni (bankdan tasodifiy),
savollar tartibini aralashtirish. Variantlar har doim aralashtiriladi.

**Jarayon:** savollar bittadan; har javobdan keyin darhol to'g'ri/noto'g'ri, to'g'ri javob va
o'qituvchi izohi. Javoblar serverda saqlanadi (sahifa yangilansa yo'qolmaydi), brauzerga to'g'ri
javoblar oldindan yuborilmaydi. Yakunda foiz, yulduzlar (o'tdi va 90%+ — 3, o'tdi — 2, 50%+ — 1)
va xatolar. Urinishlar cheklanmagan, eng yaxshi natija hisobga olinadi; o'tilsa dars tugatilgan
bo'ladi.

**Dars testi va keyingi dars (14-qadam).** Onlayn o'quvchi video darsdan keyin testni asosan
Telegram botda ishlaydi (sayt botga bir bosishda yo'naltiradi; saytda zaxira). Test **70% va undan
yuqori** bo'lsa keyingi dars ochiladi; kam bo'lsa — qayta urinish (har safar savollar bankidan
boshqa savollar, to'g'ri javoblar test o'tilgach ko'rsatiladi). Offlayn guruhda dars ustoz
"Dars o'tildi" deb belgilaganda ochiladi va test keyingi darsni to'smaydi. O'tish bali har test
uchun admin'da sozlanadi.

**O'qituvchi uchun:** savollarni oddiy matn formatida bir yo'la kiritish ("Tez kiritish"), har
savol bo'yicha to'g'ri javoblar foizi, guruh sahifasida o'quvchilar natijasi.

**Keyinroq:** kodni sandbox'da ishga tushirish (Judge0), vaqt chegarasi, urinishlar limiti,
yakuniy imtihon (sertifikat bilan), AI tushuntirishi va AI bilan savol tuzish, qisman ball.
Vaqt chegarasi va bitta urinish — oylik imtihonda (4.7.1).

### 4.7.1. Oylik imtihon (2-bosqich, 15-qadam)

Har oy oxirida kurs bo'yicha imtihon: **20 ta test + 5 ta amaliy topshiriq** (buyurtmachi talabi).
Standart qiymatlar, admin kurs bo'yicha o'zgartiradi:

- Kurs bo'yicha yoqiladi va har oy o'zi ochiladi (oyning 25-kunidan oxirgi kunigacha); qatnashadi —
  kursning faol o'quvchilari (guruhli va guruhsiz).
- **Test qismi:** shu oy o'tilgan modullar savollaridan tasodifiy 20 ta, 40 daqiqa, bitta urinish.
  Vaqt serverda hisoblanadi; to'g'ri javoblar imtihon yopilgach ko'rsatiladi.
- **Amaliy qism:** 5 ta topshiriq (kod, fayl, rasm yoki havola), imtihon yopilguncha topshiriladi;
  o'qituvchi 0–100 baholaydi.
- **Natija:** test 50% + amaliy 50%, o'tish — 60%. O'quvchiga, guruh reytingiga va XP ga (ota-onaga —
  ota-ona rejimi bilan). Kelolmaganlarga o'qituvchi alohida muddat beradi.
- Test qismi **saytda ham, botda ham** (kelishildi): bitta urinish — qayerda boshlansa, o'sha
  yerda davom etadi. Amaliy qism — saytda.
- Har oyning 20-kuni keyingi imtihon qoralamasi o'zi yaratiladi, o'qituvchi amaliy topshiriqlar va
  modullarni tanlab "Tayyor" qiladi; tayyor bo'lmagani ochilmaydi (admin'da ogohlantirish).

### 4.8. Uy vazifalari va loyiha topshirish (2-bosqich, 11-qadam)

**O'qituvchi belgilaydi** (admin'da, dars sahifasida): topshiriq matni va ixtiyoriy muddat.
Har bir darsda bitta vazifa.

**Topshirish usullari** (istalgan birikmada): izoh, kod (tili bilan), havola (GitHub, sayt,
Scratch) va fayllar — rasm, arxiv (ZIP), hujjat, kod fayli; 5 tagacha, har biri 20 MB gacha.

**Jarayon:**
```
O'quvchi yuboradi → Tekshirilmoqda
  → O'qituvchi (guruh ustozi, guruh yo'q bo'lsa — kurs ustozi) ko'rib chiqadi
  → Qabul qilindi (baho 0–100 + izoh) | Qayta ishlash kerak (izoh)
  → Qaytarilgan bo'lsa, o'quvchi yangi urinish yuboradi (oldingilari tarixda qoladi)
```

**Talablar:**
- O'qituvchi javobni platformadan chiqmasdan ko'radi: kod, rasmlar, fayllar, oldingi urinishlar.
- Navbat: tekshirilmagan javoblar, eng eskisi tepada; 48 soatdan oshganlari admin statistikasida
  muammo sifatida chiqadi.
- **Yuklangan kod serverda hech qachon ishga tushirilmaydi**, arxivlar ochilmaydi. Fayl turlari
  ro'yxat bo'yicha qabul qilinadi, fayllar yopiq storage'da, qisqa muddatli havola bilan beriladi.
- Yangi javob va natija haqida kabinet va Telegram orqali xabar (4.12).

**Keyinroq:** AI dastlabki tekshiruv (faqat tavsiya, bahoni o'qituvchi qo'yadi), o'xshashlik
tekshiruvi (MOSS/JPlag uslubida), arxiv ichini ko'rish, antivirus, audio/video izoh, rubrika,
ommaviy portfolio.

### 4.8.1. Jonli darslar va davomat (2-bosqich, 13-qadam)

- **Jadval:** guruh darslari — onlayn (Google Meet yoki Zoom havolasi bilan) yoki offlayn (xonada).
  Guruhga haftalik jadval qo'yiladi (masalan, Du/Chor/Ju 18:00); darslar 14 kun oldinga o'zi
  yaratiladi, bittasini o'zgartirish yoki bekor qilish mumkin. Meet havolasi qo'lda qo'yiladi
  (Google API kerak emas).
- **O'quvchi:** kabinetdagi "Jadval" va bosh sahifada yaqin dars; onlayn darsda "Qo'shilish" tugmasi
  boshlanishdan 15 daqiqa oldin ochiladi; o'tgan darslar — davomat holati va yozuv havolasi bilan.
- **Eslatmalar:** dars kuni oldindan va 30 daqiqa oldin (kabinet va Telegram); bekor qilinsa yoki
  yozuv qo'shilsa — xabar.
- **Davomat:** o'qituvchi belgilaydi — keldi, kechikdi, kelmadi, sababli. Onlayn darsda
  "Qo'shilish"ni bosganlar oldindan "keldi" deb belgilanadi. Kelmaganlarga xabar (ota-ona
  rejimida — ota-onaga ham). Guruh sahifasida har o'quvchining davomat foizi; ketma-ket 2 marta
  kelmaganlar — admin "muammolar" ro'yxatida.
- **"Dars o'tildi" (offlayn):** o'qituvchi darsga mavzuni (kurs darsini) belgilaydi — shu dars
  guruh o'quvchilari uchun ochiladi, testi botga (kelmaganlarga ham), uy vazifasi saytga chiqadi.
  Offlayn o'quvchiga ustoz ochmagan darslar yopiq.

### 4.9. AI yordamchi [B2]

**Imkoniyatlar:**

| Funksiya | Tavsif |
|---|---|
| Dars bo'yicha chat | Dars transkripti, materiallari va kurs dasturi asosida (RAG) javob beradi. Manbani ko'rsatadi ("3-dars, 04:12") |
| Kod tushuntirish | Talaba kodini joylaydi, AI xatoni topadi va tushuntiradi. **Tayyor yechimni darhol bermaydi**, avval yo'naltiruvchi savollar va ishoralar beradi |
| Test xatolarini tushuntirish | Xato javob nima uchun noto'g'ri ekanini va qaysi darsga qaytish kerakligini aytadi |
| Shaxsiy o'quv reja | Maqsad va haftalik vaqt asosida kurslar va darslar jadvalini tuzadi |
| Keyingi qadam tavsiyasi | Progress va zaif mavzular asosida |
| Loyiha review | 4.8-bo'limga qarang |
| Soddalashtirilgan rejim | Qisqa jumlalar, oddiy so'zlar, misollar bilan **[B3]** |
| Support bot | Platforma bo'yicha savollar (4.13-bo'lim) **[B3]** |

**Til:** AI foydalanuvchi yozgan tilda javob beradi (o'zbek lotin/kirill, rus, ingliz).

**Texnik talablar:**
- **Model:** Anthropic Claude API. Model nomi `.env` orqali sozlanadi. Taklif: murakkab vazifalar (chat, review) uchun Claude Sonnet, oddiy va ommaviy vazifalar (tasniflash, qisqa tushuntirish) uchun Claude Haiku.
- **RAG:** darslar transkripti va materiallari bo'laklarga bo'linib, vektor bazada saqlanadi (PostgreSQL + `pgvector`).
- **Javoblar streaming** orqali chiqadi.
- **Limitlar:**
  - Har bir talaba uchun kunlik limit: xabarlar soni va token (tarifga qarab sozlanadi).
  - Limit tugaganda tushunarli xabar chiqadi.
  - Admin paneldan umumiy oylik budjet va ogohlantirish chegarasi belgilanadi.
- **Xarajatni kamaytirish:** prompt caching (tizim prompti va dars konteksti keshlanadi), qisqa tarix (so'nggi N ta xabar + xulosa).

**Xavfsizlik va sifat:**
- AI'ga shaxsiy ma'lumot (telefon, to'liq ism) yuborilmaydi.
- **Prompt injection'dan himoya:** talaba matni va yuklangan kod "ma'lumot" sifatida beriladi; tizim ko'rsatmalarini o'zgartirib bo'lmaydi.
- AI faqat ta'lim va platforma mavzularida gaplashadi.
- **Test paytida AI o'chiriladi.**
- Har bir javobga 👍/👎 baho. Yomon baholangan javoblar instruktor va admin ko'rib chiqishi uchun saqlanadi.
- AI suhbatlari 90 kun saqlanadi, keyin anonimlashtiriladi.
- **Sifatni baholash:** har bir til uchun 50+ savoldan iborat test to'plami (eval). Promptlar yoki model o'zgarganda javoblar sifati qayta tekshiriladi.

### 4.10. Sertifikatlar (2-bosqich, 15-qadam)

**Berish sharti** (kurs uchun sozlanadi): barcha darslar tugatilgan; dars testlari o'tilgan;
uy vazifalari qabul qilingan; oylik imtihonlar o'rtachasi o'tish balidan yuqori. Shartlar bajarilganda
sertifikat avtomatik beriladi va o'quvchiga (ota-onaga ham) xabar boradi.

**Sertifikat tarkibi:** talaba ismi, kurs nomi, sana, ball, unikal raqam va QR kod. 3 tildan
birida, saytda A4 sahifa; PDF — brauzerning "PDF sifatida saqlash" orqali (serverga qo'shimcha
kutubxona kerak emas). Offlayn guruh o'quvchisida "darslar tugatilgan" — guruhda o'tilgan darslar.

**Talablar:**
- Ommaviy tekshirish sahifasi `/verify/[code]`: sertifikat haqiqiymi, kimga va qachon berilgan.
- Admin sertifikatni bekor qila oladi (sabab ko'rsatiladi). Tekshirish sahifasida "Bekor qilingan" deb chiqadi.
- Telegram'da ulashish va "LinkedIn'ga qo'shish" tugmalari.

### 4.11. To'lov tizimi

**To'lov turlari:**
- Kursni bir martalik sotib olish **[B1]**.
- Obuna (oylik/yillik) **[B2]**.
- Kurslar to'plami (bundle) **[B2]**.

**To'lov tizimlari:**
- **Click** (SHOP API, Prepare/Complete) **[B1]**.
- **Payme** va **Uzum** **[B2]**.
- Obuna uchun avtomatik takroriy to'lov: Click yoki Payme karta tokenizatsiyasi **[B2]**.

**Majburiy texnik talablar** **[B1]**:
- Summa har doim serverda hisoblanadi, clientdan kelgan summaga ishonilmaydi.
- To'lov tizimi so'rovlari uchun imzo tekshiruvi.
- Summa tekshiruvi.
- Idempotentlik: bitta tranzaksiya ikki marta qayta ishlanmaydi.
- To'lov tizimi bilan bo'lgan barcha so'rov va javoblar to'liq log qilinadi.
- To'lanmagan buyurtma 30 daqiqada `EXPIRED` bo'ladi.
- Kurs faqat to'lov tizimining tasdiqlash so'rovidan keyin ochiladi (return URL'ga qaytish isbot emas).

**Fiskalizatsiya** **[B1]**: har bir to'lov uchun fiskal chek (MXIK kodi bilan). Chek havolasi talabaga SMS yoki email orqali yuboriladi.

**Promo-kodlar** **[B2]**:
- Chegirma turi: foiz yoki qat'iy summa.
- Cheklovlar: amal qilish muddati, umumiy foydalanish limiti, har bir foydalanuvchi uchun limit.
- Qo'llanish doirasi: muayyan kurslar yoki hammasi.
- Manager yaratadi.

**Refund:**
- Refund shartlari: to'lovdan 3 kun ichida **va** kursning 20% idan kami ko'rilgan bo'lsa (yakuniy shartni yurist tasdiqlaydi).
- Admin qo'lda belgilaydi, pul Click kabineti orqali qaytariladi **[B1]**.
- Talaba paneldan refund so'rovi yuboradi. Tizim shartlarni avtomatik tekshiradi; admin tasdiqlagach, pul to'lov tizimi API'si orqali qaytariladi **[B2]**.

**Qo'shimcha:**
- Qo'lda kirish berish: naqd to'lov, grant va boshqa holatlar uchun **[B1]**.

### 4.12. Bildirishnomalar

**Kanallar:**

| Kanal | Bosqich |
|---|---|
| Ichki (platformada, 🔔 "Xabarlar") | B2, 10-qadam |
| Telegram bot — asosiy tashqi kanal (bepul) | B2, 10-qadam |
| SMS — kodlar va Telegram'i yo'qlarga zaxira (pullik, Eskiz shabloni kerak) | B1 |
| Web push | B3 |

Telegram ulanadi: Telegram orqali ro'yxatdan o'tganda (kirish oynasi xabar yuborishga ruxsat
so'raydi) yoki kabinet sozlamalaridagi "Telegram'ni ulash" tugmasi orqali (botga bir martalik havola).

**Hodisalar:**
- SMS kod.
- To'lov muvaffaqiyatli, chek havolasi.
- Kurs ochildi.
- Offlayn to'lov muddati tugayapti (3 kun qolganda) va tugadi.
- Admin paneldan yuborilgan xabar: o'quv xabari yoki aksiya.
- Uy vazifasi: yangi javob (o'qituvchiga), natija (o'quvchiga).
- O'qishni to'xtatib qo'yganlarga eslatma — 3 va 7 kun, keyingi dars havolasi bilan (ikki haftadan
  keyin yozilmaydi).
- Keyingi qadamlarda: jonli dars eslatmasi, kelmagan dars va yangi dars ochildi (13), dars testi
  botda va yangiliklar botdagi hammaga (14), oylik imtihon (15), kunlik topshiriqlar va shtraflar (16).
- Savolingizga javob berildi, ticket yangilandi, sertifikat tayyor — tegishli bo'limlar bilan.

**Talablar:**
- Foydalanuvchi Telegram xabarlarini o'chira oladi. Kabinetdagi xabarlar va SMS kodlari o'chirilmaydi.
- Aksiya va yangiliklar Telegram va SMS orqali faqat alohida rozilik bilan yuboriladi (ro'yxatdan
  o'tishda yoki sozlamalarda; oldindan belgilanmagan). Kabinetda hammaga ko'rinadi.
- Barcha xabarlar navbat orqali yuboriladi (qayta urinish bilan) va foydalanuvchi tilida.
- Tungi vaqtda (22:00–09:00) aksiya va eslatma xabarlari yuborilmaydi.
- Admin ommaviy xabarni yuborishdan oldin qabul qiluvchilar sonini va SMS narxini ko'radi.

**Kunlik statistika (2-bosqich, 10-qadam):** admin bosh sahifasida bugungi ro'yxatdan o'tishlar,
kurs tanlaganlar, to'lovlar, arizalar, AI va muammolar (javobsiz arizalar, to'lov va SMS xatolari,
tizim xatolari); har kuni kechqurun direktorga Telegram'da qisqa hisobot. Batafsil — PLAN.md §7A.6.

### 4.12.1. AI sotuv maslahatchisi (2-bosqich, 8-qadam)

Buyurtmachining asosiy muammosi: mijozlar ish vaqtidan keyin yozadi va javob olmaydi. Shuning uchun
4.13-bo'limdagi "AI support bot" oldinga olindi va sotuvga yo'naltirildi:

- Kanallar: saytdagi chat (kasb testi yonida va har sahifada) va Telegram bot.
- Javob faqat bazadagi ma'lumot asosida: kurslar, narxlar, FAQ, aloqa, ish vaqti, admin yozgan
  qo'shimcha ma'lumot. Bilmagan narsani o'ylab topmaydi.
- Mijoz raqamini qoldirsa — ariza (manba: AI), menejerlarga Telegram xabar.
- Telefon raqamlari modelga yuborilmaydi (belgi bilan almashtiriladi) — 4.9 talabiga mos.
- Kunlik va oylik budjet, suhbat va IP limitlari; budjet tugasa yoki API ishlamasa, oddiy rejim
  raqam so'rashda davom etadi.
- Suhbatlar 90 kun saqlanadi, keyin anonimlashtiriladi; har bir javobga 👍/👎.

### 4.12.2. Telegram bot (2-bosqich, 14-qadam)

Yangi bot — hammasi bitta botda (AI maslahatchi ham). **Oddiy tugmalar, Mini App yo'q:** video
darslar faqat saytda, XP va reyting — saytda.

- **Majburiy obuna:** botdagi har bir amalda kanal a'zoligi tekshiriladi (o'tgani 30 daqiqa
  eslab qolinadi); obuna bo'lmaganga kanal havolasi va "✅ Obuna bo'ldim". Kanallar ro'yxati
  admin'da. Bot kanalda administrator bo'lmasa, a'zolikni bilib bo'lmaydi — obuna so'ralmaydi
  va admin bosh sahifasida ogohlantirish chiqadi. Xodimlardan va saytda obuna talab qilinmaydi.
- **Ro'yxatdan o'tish — bitta akkaunt, ikki eshik:** saytda telefon va SMS kod; botda "Telefonni
  yuborish" (raqamni Telegram tasdiqlaydi, SMS kerak emas). Bir telefon — bitta akkaunt: botga
  saytdagi raqam yuborilsa, akkaunt ulanadi. Sayt → bot va bot → sayt o'tishlari bir martalik
  havolalar bilan (qayta kirish so'ralmaydi). Xodim akkauntlari bot orqali ulanmaydi.
- **Menyu:** kurslarim (saytga bir bosishda), testlar, jadval ("Qo'shilish"), do'stni taklif
  qilish, savol berish (AI maslahatchi, kerak bo'lsa menejer), sozlamalar (til, yangiliklar,
  saytga kirish); bugungi topshiriqlar — 4.16 bilan. Menyu tugmasi yoki test javobi bo'lmagan
  har qanday matn — AI maslahatchiga.
- **Dars testlari** — botda, tugmalar bilan (4.7: 70% bilan keyingi dars): 5 tur, har javobdan
  keyin faqat to'g'ri/noto'g'ri; to'g'ri javoblar va izohlar test o'tilgach (saytda ham). Saytdagi
  test kartasida "Telegram'da ishlash" (asosiy) va "Saytda ishlash". Offlayn guruhda ustoz "Dars
  o'tildi" deganda botga "Testni boshlash" tugmali xabar.
- **Saytga o'tish:** botdagi tugmalar bir martalik havola bilan parolsiz kiritadi (10 daqiqa;
  eskirgan bo'lsa — kirish sahifasi, keyin kerakli sahifa) — faqat raqami Telegram orqali
  tasdiqlangan (kontakt yuborgan) chatga. Xodimga bunday havola berilmaydi.
- **Yangiliklar:** admin paneldan qo'shilgan yangilik kabinetga va **botdagi hammaga** (/start
  bosganlarning hammasi; faqat filtrsiz xabarda), rasm bilan; har kimga bir marta (Telegram'i
  ulangan o'quvchi xabarni odatdagidek oladi); 22:00–09:00 da yozilgani ertalab; har xabar ostida
  "Yangiliklarni o'chirish".
- **Referal havolasi:** har kimning shaxsiy havolasi (bot va sayt); kim taklif qilgani ro'yxatdan
  o'tishda yoziladi (mukofot — 4.16).
- **Botdagi admin panel** (`/admin` yoki menyudagi "📊 Admin panel" — faqat statistikani ko'rish
  huquqi borlarga: direktor, admin, menejer; Telegram'i akkauntiga ulangan bo'lsa): foydalanuvchilar
  (bot — jami, yangi, ro'yxatdan o'tgan va o'tmagan, bloklagan, yangiliklarni o'chirgan; sayt
  o'quvchilari — jami, yangi, Telegram ulangan, Kids), o'qish, savdo va muammolar — admin bosh
  sahifasidagi raqamlar bilan bir xil; davr: bugun, kecha, 7 va 30 kun.

### 4.12.3. Ota-ona rejimi (SIFAT Kids bilan birga, oxirida)

Ota-onaga farzandning hisoboti, imtihon natijasi va davomati; bitta telefonda bir nechta farzand.
SIFAT Kids uchun yangi g'oyalar bilan birga rejalanadi.

### 4.13. Qo'llab-quvvatlash (Support) [B3]

**Kanallar:**
- **AI support bot (24/7):** FAQ va platforma bo'yicha savollarga javob beradi. Hal qila olmasa, ticket yaratishni taklif qiladi.
- **Ticket tizimi:**
  - Kategoriyalar: to'lov, texnik, kurs mazmuni, boshqa.
  - Holatlar: `OPEN` → `IN_PROGRESS` → `WAITING_USER` → `RESOLVED` → `CLOSED`.
  - Ustuvorlik darajasi, fayl biriktirish.
  - Kurs mazmuni bo'yicha ticketlar shu kurs instruktoriga yo'naltiriladi.
- **Jonli operator (09:00–23:00):** platformadagi chat va Telegram. Ish vaqtidan tashqarida murojaat avtomatik ticketga aylanadi.

**SLA:**

| Murojaat turi | Birinchi javob |
|---|---|
| To'lov muammolari | 2 soat (ish vaqtida) |
| Boshqa muammolar | 12 soat |

**Operator paneli:**
- Ticketlar navbati.
- Tayyor javob shablonlari (3 tilda).
- Foydalanuvchining kurslari, to'lovlari va oxirgi xatolari bir sahifada.

**Hisobotlar:** javob vaqti, hal qilingan ticketlar, qoniqish bahosi (CSAT).

### 4.14. Forum va dars savol-javoblari

**Dars ostida savol-javob** **[B2]**:
- Talaba savol beradi; instruktor va boshqa talabalar javob beradi.
- Kod bloklari, "Eng yaxshi javob" belgisi.

**Kurs forumi** **[B3]**:
- Mavzular, teglar, qidiruv, "foydali" ovozlar.

**Moderatsiya:**
- Shikoyat qilish tugmasi.
- Taqiqlangan so'zlar filtri.
- Instruktor va support xabarlarni yashira oladi.
- Qoida buzuvchini vaqtincha bloklash.

### 4.15. Sharhlar va reyting [B2]

- Kursni sotib olgan va uning ≥ 30% ini o'tgan talaba 1–5 yulduz va matnli sharh qoldiradi.
- Instruktor sharhga javob beradi.
- Admin moderatsiya qiladi.
- Kurs reytingi katalog va kurs sahifasida ko'rinadi.

### 4.16. Gamifikatsiya: XP, kunlik topshiriqlar, reyting, referal va do'kon (2-bosqich, 16–17-qadamlar)

- **Kunlik topshiriqlar:** har kuni ertalab bot 3 ta topshiriq yuboradi — har kuni boshqacha,
  o'quvchi qayerga yetganiga qarab: darsni ko'rish, dars testidan o'tish, botda takrorlash (5 ta
  savol), uy vazifasini topshirish, offlaynda darsga vaqtida kelish. Uchalasi bajarilsa — bonus va
  kunlik seriya davom etadi (topshiriq berilmagan kun seriyani uzmaydi). Botda takrorlash faqat
  Telegram ulangan va o'tilgan testlarda yetarli savol bo'lsa beriladi. Davomat uchun XP va shtraf —
  o'qituvchi davomatni saqlaganda (o'zgartirsa — qayta hisoblanadi).
- **XP va coin — ikki valyuta** (kelishildi): XP — reyting uchun, sarflanmaydi; coin — do'kon
  uchun, har topilgan XP bilan teng coin beriladi, referal mukofotlari coinda. Topshiriqlar,
  testlar, vazifalar, imtihon va davomat uchun. Qiymatlar admin'da; faqat serverda tasdiqlangan
  harakatlar hisoblanadi. XP, coin va tarixi — saytda (botda — faqat bugungi topshiriqlar).
- **Shtraflar (faqat XP, coin'ga tegmaydi):** kunlik topshiriq bajarilmasa, darsga sababsiz kelmasa, kechiksa, uy
  vazifasi muddatidan kechiksa. Test yiqilgani uchun shtraf yo'q. XP 0 dan pastga tushmaydi; har
  shtraf sababi bilan ko'rinadi, ustoz yoki admin bekor qila oladi.
- **Reyting (saytda):** haftalik, oylik va umumiy; guruh va kurs bo'yicha. Faqat ism va
  familiyaning bosh harfi; eng yaxshi 10 ta va o'z o'rni; reytingdan yashirinish mumkin. Haftalik
  g'oliblar kanalga e'lon qilinadi (ixtiyoriy).
- **Referal (coin + chegirma):** do'st shaxsiy havola bilan ro'yxatdan o'tadi. Do'st telefonini
  tasdiqlab, birinchi darsni tugatsa — taklif qilganga coin. Do'st birinchi to'lovda chegirma oladi
  (standart 10%). Do'st to'lov qilsa — taklif qilganga ko'proq coin va keyingi to'lovi uchun
  chegirma kuponi (standart 10%, bitta to'lovga bitta kupon). O'zini taklif qilib bo'lmaydi.
- **Coin do'koni (17-qadam):** sovg'alar (raqamli va jismoniy, zaxira bilan), buyurtma va topshirish.
- **Keyinroq (SIFAT Kids bilan):** o'yinlar (duel, blits, klaviatura trenajyori, turnirlar), Kids
  ligasi. Haftalik maqsad — keyinroq.

### 4.17. Instruktor paneli [B2]

**Mening kurslarim:**
- Kurs, modul va dars yaratish/tahrirlash.
- Video va materiallar yuklash.
- Kursni tasdiqlashga yuborish.

**O'quv kontenti:**
- Testlar va savollar banki.
- Loyiha topshiriqlari va rubrikalar.

**Talabalar bilan ishlash:**
- Baholash navbati (loyihalar).
- Dars savollari (javob berilmaganlar birinchi).
- O'z kurslari talabalari ro'yxati: progress va natijalar (kontaktlarsiz).

**Statistika:**
- Talabalar soni, tugatish darajasi.
- Qaysi darsda talabalar kursni tashlab ketadi.
- Test savollari statistikasi, reyting va sharhlar.

**Subtitlar va O'IT** **[B3]**: subtitr tahrirlash, O'IT videosini yuklash va sinxronlash.

### 4.18. Manager paneli [B2]

**Arizalar (CRM):**
- Arizalar va ularning holatlari: `NEW` → `CONTACTED` → `CONVERTED` / `REJECTED`.
- Menejerga biriktirish, izohlar, qayta qo'ng'iroq eslatmasi.

**Sotuvlar va moliya:**
- Kunlik, haftalik va oylik tushum.
- Kurslar va to'lov tizimlari bo'yicha taqsimot.
- O'rtacha chek, refundlar, obunalar va ularning bekor qilinishi (churn).

**Marketing:**
- Promo-kodlar va ularning samaradorligi.
- UTM hisoboti: qaysi kanal ko'proq ariza va to'lov keltirgan.

**Eksport:** CSV/XLSX.

### 4.19. Admin panel

Admin panel — **Django Admin** (Unfold temasi), manzili `/admin/`. Faqat xodimlar (`is_staff`) kiradi, ruxsatlar Django Group'lari va permission'lari orqali. Kontent 3 tilda til tablari bilan tahrirlanadi. Instruktor va Manager panellari (4.17, 4.18) frontend'da alohida yoziladi.

**[B1]:**
- Dashboard: kunlik statistika, voronka va muammolar (2-bosqich, 10-qadam; 4.12).
- Kurslar, kategoriyalar, darslar, video.
- Foydalanuvchilar (bloklash, qo'lda kirish berish).
- Buyurtmalar va refund.
- Arizalar (holat, izoh, CSV eksport).
- Landing kontenti va huquqiy sahifalar.

**[B2]:**
- Rollarni boshqarish.
- Instruktor kurslarini tasdiqlash.
- Sertifikat shablonlari.
- AI sozlamalari (model, limitlar, budjet, tizim promptlari).
- Xabarnomalar: ommaviy xabar yuborish (auditoriya, kanallar, natija). Avtomatik xabarlar
  matni kodda, 3 tilda — alohida shablon muharriri kerak emas.
- Tizim sozlamalari.

**[B3]:**
- Analitika dashboardi (4.19.1-bo'lim).
- Support boshqaruvi.
- Forum moderatsiyasi.

**Audit log** **[B1]**: kim, qachon, nimani o'zgartirgan. Narxlar, rollar, refund, qo'lda kirish berish, bloklash va o'chirish amallari yoziladi.

#### 4.19.1. Analitika [B3]

- **Voronka:** tashrif → ariza/ro'yxatdan o'tish → to'lov → 1-dars → kursni tugatish.
- **Kogorta retention:** haftalar bo'yicha.
- **Kurslar bo'yicha:** tugatish darajasi, o'rtacha ball, dars bo'yicha tashlab ketish.
- **AI:** so'rovlar soni, xarajat, 👍/👎 nisbati.
- **Texnik:** video xatolari, sahifa tezligi.

### 4.20. Ko'p tillilik (i18n) [B1]

- **Tillar:** o'zbek (lotin, asosiy), rus, ingliz.
- **URL:** `/uz/...`, `/ru/...`, `/en/...` (next-intl).
- **Interfeys matnlari:** JSON fayllarda. Kodda qattiq yozilgan matn bo'lmaydi (lint bilan tekshiriladi).
- **Kontent** (kurslar, testlar, sertifikatlar, bildirishnomalar, landing): DB'da har bir til uchun alohida qiymat. Tarjima yo'q bo'lsa, o'zbekcha ko'rsatiladi. Admin panelda qaysi tarjimalar yetishmayotgani ko'rinadi.
- **Video:** asosan bitta tilda. Boshqa tillar uchun subtitr **[B3]**.
- **Formatlash:** sana, vaqt, raqam va narx `Intl` orqali tilga mos.

### 4.21. Accessibility va O'IT [B3]

> 1–2-bosqichlarda bu funksiyalar yo'q. Lekin 1-bosqichdan boshlab quyidagi **asoslar majburiy**:
> - Semantik HTML.
> - Klaviatura bilan to'liq navigatsiya.
> - Ko'rinadigan focus indikatori.
> - Rasmlarda `alt` matni.
> - Formalarda label'lar.
> - Kontrast ≥ 4.5:1.
> - Accessible komponentlar (shadcn/ui, Radix).
>
> Shunda 3-bosqichda hammasini qayta yozishga to'g'ri kelmaydi.

#### 4.21.1. WCAG 2.1 AA

- Barcha interaktiv elementlarda ARIA label'lar; ekran o'quvchilar (NVDA, JAWS, VoiceOver, TalkBack) bilan sinalgan.
- **Sozlamalar paneli:**
  - Shrift o'lchami (100–200%).
  - Yuqori kontrast rejimi.
  - Disleksiyaga mos shrift.
  - Animatsiyalarni o'chirish (`prefers-reduced-motion`).
  - Qatorlar orasidagi masofa.
- "Asosiy kontentga o'tish" (skip link).
- Sahifa tilini to'g'ri belgilash (`lang`).
- Xatolar haqidagi xabarlar ekran o'quvchiga e'lon qilinadi.
- **Kod muharriri** (test va AI chat'da) klaviatura va ekran o'quvchi bilan ishlaydi (masalan, CodeMirror 6).

#### 4.21.2. Subtitlar va transkript

- WebVTT, 3 til.
- Jarayon: ASR → inson tahriri → nashr.
- Subtitr ko'rinishini sozlash: o'lcham, fon, rang.
- Transkript ko'zi ojiz va kar foydalanuvchilar uchun ham, SEO uchun ham ishlaydi.
- Kodni ekranda ko'rsatadigan darslar uchun: **audio-tavsif yoki kengaytirilgan transkript** (ekranda nima yozilayotgani matnda).

#### 4.21.3. O'IT tarjimon tizimi

**Overlay pleyer:**
- Asosiy video ustida tarjimon videosi.
- Burchakni o'zgartirish, o'lchamni o'zgartirish (S/M/L), yoqish/o'chirish.

**Sinxronizatsiya:**
- Asosiy video "master clock" hisoblanadi.
- Tarjimon videosi har 1 soniyada tekshiriladi. Farq > 0.3 soniya bo'lsa, tuzatiladi.
- Asosiy video buferlanayotganda tarjimon videosi ham to'xtaydi.

**Burn-in zaxira varianti:**
- Har bir dars uchun tarjimon yopishtirilgan HLS versiya avtomatik yaratiladi.
- Qachon ishlatiladi:
  - iOS Safari'da (u yerda to'liq ekranda overlay ishlamaydi).
  - Foydalanuvchi o'zi tanlaganda.

**O'IT video spetsifikatsiyasi:**
- MP4 (H.264), ≥ 720p, 30 fps.
- Bir xil ochiq fon.
- Asosiy video bilan timecode bo'yicha sinxron.

**Ko'rsatkichlar va profil:**
- Kurs sahifasida va katalog filtrida "O'IT tarjimon" belgisi.
- Accessibility profilida "O'IT'ni avtomatik yoqish" sozlamasi.

**IT atamalarining O'IT lug'ati:**
- Ommaviy bepul sahifa `/sign-dictionary`.
- Har bir atama uchun video, izoh, misol va 3 tildagi tarjima.
- Tarjimonlar va kar hamjamiyati bilan birga ishlab chiqiladi.
- Barcha darslarda yagona atamalar ishlatiladi.

#### 4.21.4. Maxsus profil

- Foydalanuvchi o'z ixtiyori bilan ehtiyojlarini belgilaydi (eshitish, ko'rish, harakat, kognitiv).
- Bu **sezgir ma'lumot**:
  - Alohida rozilik bilan olinadi.
  - Faqat sozlamalarni avtomatik moslash uchun ishlatiladi.
  - Admin ham faqat umumiy (agregat) statistikani ko'radi.
  - Instruktorga ko'rsatilmaydi.

---

## 5. Sahifalar xaritasi

Barcha ommaviy va o'quvchi sahifalari `/{locale}` prefiksi bilan ochiladi (`/uz`, `/ru`, `/en`).

### 5.1. Ommaviy sahifalar

| URL | Sahifa | Bosqich |
|---|---|---|
| `/` | Landing | B1 |
| `/courses` | Katalog | B1 |
| `/courses/[slug]` | Kurs tafsiloti | B1 |
| `/courses/[slug]/preview/[lessonId]` | Bepul dars | B1 |
| `/paths`, `/paths/[slug]` | O'quv yo'llari | B2 |
| `/pricing` | Narxlar va obuna | B2 |
| `/instructors`, `/instructors/[slug]` | Ustozlar | B2 |
| `/about` | Platforma haqida | B1 |
| `/contacts` | Kontaktlar | B1 |
| `/verify/[code]` | Sertifikatni tekshirish | B2 |
| `/u/[username]` | Ommaviy portfolio | B2 |
| `/accessibility` | Accessibility haqida | B3 |
| `/sign-dictionary` | IT atamalarining O'IT lug'ati | B3 |
| `/offer`, `/privacy`, `/refund-policy` | Huquqiy sahifalar | B1 |
| `/auth/login`, `/auth/register`, `/auth/forgot-password` | Autentifikatsiya | B1 |

### 5.2. O'quvchi sahifalari

| URL | Sahifa | Bosqich |
|---|---|---|
| `/checkout/[type]/[id]` | Buyurtmani tasdiqlash | B1 |
| `/payment/result` | To'lov natijasi | B1 |
| `/dashboard` | Asosiy panel | B1 |
| `/dashboard/courses` | Mening kurslarim | B1 |
| `/dashboard/courses/[slug]/lessons/[id]` | Dars sahifasi | B1 |
| `/dashboard/courses/[slug]/tests/[id]` | Test | B2 |
| `/dashboard/courses/[slug]/projects/[id]` | Loyiha topshirish | B2 |
| `/dashboard/progress` | Progress va statistika | B2 |
| `/dashboard/certificates` | Sertifikatlar | B2 |
| `/dashboard/projects` | Mening loyihalarim | B2 |
| `/dashboard/plan` | AI o'quv reja | B2 |
| `/dashboard/notifications` | Bildirishnomalar | B2 |
| `/dashboard/orders` | Buyurtmalar | B1 |
| `/dashboard/subscription` | Obuna | B2 |
| `/dashboard/support` | Ticketlar | B3 |
| `/dashboard/settings` | Profil va xavfsizlik | B1 |
| `/dashboard/settings/accessibility` | Accessibility sozlamalari | B3 |

### 5.3. Instruktor sahifalari

| URL | Sahifa | Bosqich |
|---|---|---|
| `/instructor` | Bosh sahifa | B2 |
| `/instructor/courses/...` | Kurslar, darslar, video | B2 |
| `/instructor/tests` | Testlar va savollar banki | B2 |
| `/instructor/reviews` | Loyihalarni baholash navbati | B2 |
| `/instructor/questions` | Dars savollari | B2 |
| `/instructor/analytics` | Statistika | B2 |

### 5.4. Manager sahifalari

| URL | Sahifa | Bosqich |
|---|---|---|
| `/manager` | Bosh sahifa | B2 |
| `/manager/leads` | Arizalar (CRM) | B2 (B1'da Django Admin'da) |
| `/manager/sales` | Sotuvlar | B2 |
| `/manager/promo-codes` | Promo-kodlar | B2 |
| `/manager/reports` | Hisobotlar | B2 |

### 5.5. Support sahifalari

| URL | Sahifa | Bosqich |
|---|---|---|
| `/support-desk` | Ticketlar va chatlar | B3 |

### 5.6. Admin panel bo'limlari

Admin panel — **Django Admin** (Unfold temasi), manzili `/admin/`, til prefiksisiz (4.19-bo'lim). Menyu bo'limlari:

| Bo'lim | Bosqich |
|---|---|
| Dashboard | B1 |
| Kurslar, kategoriyalar, ustozlar, darslar, video | B1 |
| Foydalanuvchilar va rollar | B1 |
| Buyurtmalar va refund | B1 |
| Arizalar | B1 |
| Sayt kontenti | B1 |
| Audit log | B1 |
| Kurslarni tasdiqlash | B2 |
| Sertifikatlar | B2 |
| AI sozlamalari va xarajat | B2 |
| Bildirishnoma shablonlari | B2 |
| Tizim sozlamalari | B2 |
| Analitika | B3 |
| Moderatsiya | B3 |

---

## 6. Texnik arxitektura

### 6.1. Texnologiyalar steki

Loyiha **ikkita mustaqil ilovadan** iborat: `frontend/` (Next.js) va `backend/` (Django). Ular monorepo emas: har birining o'z paket fayli, `Dockerfile` va `.env` fayli bor, bir-birining kodini import qilmaydi. Ular faqat HTTP (REST API) orqali bog'lanadi.

**Umumiy:**

| Kategoriya | Texnologiya | Sabab |
|---|---|---|
| API tiplari | Backend **OpenAPI** sxemasini chiqaradi (`drf-spectacular`) → frontend `openapi-typescript` bilan tip generatsiya qiladi | Umumiy paketsiz tiplar sinxron |
| Konteynerlar | **Docker**, **Docker Compose** (local va production) | |
| Reverse proxy | **nginx**: `/` → frontend; `/api/`, `/admin/`, `/static/` → backend; HLS kesh | Bitta domen, cookie va CSRF oddiy, CORS kerak emas |
| Testlar | **pytest** (backend), **Vitest** (frontend), **Playwright**, **axe-core** | |
| CI/CD | **GitHub Actions**, har bir loyiha uchun alohida workflow | |
| Monitoring | **Sentry**, uptime monitor | |

**Frontend (`frontend/`):**

| Kategoriya | Texnologiya | Sabab |
|---|---|---|
| Framework | **Next.js** (App Router), ish boshlanganda oxirgi barqaror versiya | SSR/SSG, SEO |
| Til | **TypeScript**, `strict: true`, `any` taqiqlangan | |
| Stil | **Tailwind CSS v4** | |
| UI | **shadcn/ui** (Radix) | Accessibility tayyor |
| 3D | **React Three Fiber**, **drei**, **@react-three/postprocessing** | Landing 3D sahnalari (4.1.1) |
| Animatsiya | **Motion** (Framer Motion; `prefers-reduced-motion` hisobga olinadi) | |
| Formalar | React Hook Form + **Zod** | |
| Server holati | **TanStack Query**; UI holati uchun Zustand (faqat kerak joyda) | |
| i18n | **next-intl** | |
| Video pleyer | **hls.js** (o'z UI bilan) | HLS, AES, keyinroq O'IT overlay |
| Grafiklar | Recharts (B2) | |
| Kod muharriri | CodeMirror 6 (B2) | |

**Backend (`backend/`):**

| Kategoriya | Texnologiya | Sabab |
|---|---|---|
| Til | **Python 3.13**, type hint'lar, `mypy` | |
| Framework | **Django 5.2 LTS** + **Django REST Framework** | ORM, migratsiyalar, admin tayyor; LTS 2028-yil aprelgacha |
| API hujjati | **drf-spectacular** (OpenAPI 3, Swagger UI) | Frontend tiplari shundan generatsiya qilinadi |
| Admin panel | **Django Admin** + **Unfold** temasi | B1 admin sahifalari (4.19) |
| Validatsiya | DRF serializer'lar | |
| Ma'lumotlar bazasi | **PostgreSQL 16+** + `pgvector` | Asosiy DB + AI uchun vektor qidiruv (B2) |
| Tarjima (kontent) | **django-modeltranslation** | Har bir til uchun alohida ustun, admin'da til tablari |
| Kesh, sessiya, navbat | **Redis** + **Celery** (davriy vazifalar — Celery beat) | Rate limit, OTP, sessiyalar, fon vazifalari |
| Auth | **Django session** (httpOnly cookie, Redis) + CSRF; parollar argon2 | Bitta domen, mobil ilova rejada yo'q |
| Fayllar | **S3-mos object storage** (django-storages; dev'da SeaweedFS, prod'da mahalliy provayder) | |
| Video | **ffmpeg** (alohida Celery worker) | HLS + AES-128 |
| Qidiruv | PostgreSQL full-text + `pg_trgm` | |
| Audit | **django-auditlog** | Kim, qachon, nimani o'zgartirgan |
| Server | gunicorn + uvicorn worker (ASGI) | SSE va keyinroq WebSocket uchun |
| Loglar | JSON loglar | |
| Paket menejer | **uv** (`pyproject.toml`, `uv.lock`) | |
| Kodni ishga tushirish | **Judge0** (self-hosted, B2) | |
| AI | **Anthropic Claude API** (B2) | |
| Real vaqt | SSE (AI streaming, B2), WebSocket — Django Channels (jonli chat, B3) | |

### 6.2. Tizim komponentlari

```
                       ┌──────────────┐
 Foydalanuvchi ──────▶ │    nginx     │──▶ HLS segmentlar (kesh)
   (brauzer)           └──┬────────┬──┘
                   /      │        │  /api, /admin, /static
                          ▼        ▼
               ┌────────────┐   ┌────────────┐      ┌──────────────┐
               │  frontend  │──▶│  backend   │◀────▶│  PostgreSQL  │
               │  Next.js   │SSR│  Django    │      │  + pgvector  │
               └────────────┘   └─────┬──────┘      └──────────────┘
                                      │                    ▲
                                      ▼                    │
                               ┌────────────┐      ┌───────┴──────┐
                               │   Redis    │◀────▶│ Celery       │
                               │  (navbat,  │      │ (backend     │
                               │  sessiya,  │      │  image'i)    │
                               │ rate limit)│      │ - worker     │
                               └────────────┘      │ - video      │
                                                   │ - beat       │
                                                   └──────┬───────┘
                                                          ▼
          ┌──────────┬──────────┬──────────┬──────────┬──────────┐
          │ Object   │ Click /  │ Eskiz    │ Telegram │ Anthropic│
          │ storage  │ Payme    │ (SMS)    │ Bot API  │ API (B2) │
          └──────────┴──────────┴──────────┴──────────┴──────────┘
                                         + Judge0 (B2, izolyatsiya qilingan server)
```

**Arxitektura tamoyillari:**
- **Frontend va backend alohida.** Frontend'da biznes mantiq va DB'ga to'g'ridan-to'g'ri kirish yo'q — faqat backend API.
- **Backend — modulli monolit:** Django app'lari domenlar bo'yicha (`users`, `catalog`, `learning`, `assessment`, `payments`, `ai`, `support`, `notifications`). Mikroservislar faqat haqiqiy ehtiyoj bo'lganda ajratiladi.
- **Og'ir ishlar faqat worker'larda:** video, AI review, xabarlar yuborish. Celery worker'lari backend bilan bir image'dan, boshqa buyruq bilan ishga tushadi.
- **Biznes mantiq servis qatlamida** (`services.py`): view va serializer'lar faqat servislarni chaqiradi. Shu qatlam testlanadi.

### 6.3. Loyiha papka tuzilmasi

```
sifatedu/
├── frontend/                    # mustaqil Next.js loyiha
│   ├── Dockerfile, package.json, .env.example
│   ├── messages/{uz,ru,en}.json
│   └── src/
│       ├── app/[locale]/(public)/ (auth)/ dashboard/ instructor/ manager/
│       ├── components/ui/       # shadcn
│       ├── components/three/    # 3D sahnalar (faqat client, lazy)
│       ├── features/<domen>/
│       └── lib/api/             # API client + generatsiya qilingan tiplar
├── backend/                     # mustaqil Django loyiha
│   ├── Dockerfile, pyproject.toml, uv.lock, manage.py, .env.example
│   ├── config/                  # settings, urls, asgi, celery
│   └── apps/<domen>/            # models, services, serializers, views, admin, tasks, tests
├── infra/nginx/, infra/scripts/
├── docker-compose.yml           # asosiy servislar
├── docker-compose.override.yml  # local (dev), avtomatik ulanadi
├── docker-compose.prod.yml      # production qo'shimchalari
└── docs/
```

---

## 7. Ma'lumotlar bazasi modellari

> Django modellari (`backend/apps/*/models.py`) va migratsiyalar har bir bosqich boshida yoziladi.
> Tarjima qilinadigan matn maydonlari django-modeltranslation orqali har bir til uchun alohida ustunda saqlanadi (`title_uz`, `title_ru`, `title_en`). Tarjima yo'q bo'lsa, o'zbekchasi qaytadi.

### 7.1. Foydalanuvchilar va kirish

| Model | Asosiy maydonlar | Bosqich |
|---|---|---|
| `User` | phone, email?, password (argon2), ism, familiya, username, locale, is_active (bloklash), utm | B1 |
| Rollar | Django `Group`: STUDENT, INSTRUCTOR, MANAGER, SUPPORT, ADMIN. Bitta foydalanuvchida bir nechta rol bo'lishi mumkin | B1 |
| `OtpCode` | phone, codeHash, purpose, attempts, expiresAt | B1 |
| `OAuthAccount` | provider (telegram, google), providerId | B2 |
| `Consent` | turi (oferta, privacy, marketing, accessibility_data), versiya, sana | B1 |
| `AccessibilityProfile` | ehtiyojlar, sozlamalar (shrift, kontrast, O'IT avto) | B3 |

### 7.2. Kontent

| Model | Asosiy maydonlar | Bosqich |
|---|---|---|
| `Category` | slug, name | B1 |
| `Instructor` | ism, rasm, lavozim, bio, tajriba, ijtimoiy tarmoqlar, user? (B2'da akkauntga bog'lanadi) | B1 |
| `Course` | slug, title, description, audience (ADULT/KIDS), ageMin?, ageMax?, studyFormat (ONLINE/OFFLINE/BOTH), isFree, priceOnline (bir martalik), priceOfflineMonthly (oylik), level, status, videoLanguage, mxikCode, unlockMode, hasSignLanguage, isFeatured | B1 |
| `CourseInstructor` | courseId, instructorId | B1 |
| `Module` | courseId, title, order | B1 |
| `Lesson` | moduleId, title, order, isPreview, videoId, signVideoId | B1 (signVideoId — B3) |
| `VideoAsset` | status, rawKey, hlsPath, duration, thumbnail, kind (MAIN, SIGN, BURNED_IN) | B1 |
| `SubtitleTrack` | lessonId, locale, fileKey, status (DRAFT, PUBLISHED) | B3 |
| `Transcript` | lessonId, locale, segmentlar (vaqt + matn) | B2 (RAG uchun) |
| `LessonMaterial` | lessonId, fayl | B1 |
| `LearningPath` / `LearningPathCourse` | kurslar ketma-ketligi | B2 |
| `ContentChunk` | manba (dars/material), matn, `embedding vector` | B2 |
| `SignTerm` | atama, video, izoh, tarjimalar | B3 |
| `SiteSettings` | kontaktlar, ijtimoiy tarmoqlar, hero matnlari, bo'limlarni yoqish/o'chirish (yagona yozuv) | B1 |
| `Advantage`, `HowStep`, `FAQItem`, `Testimonial` | landing bo'limlari (tartib, nashr holati) | B1 |
| `LegalPage` | slug, sarlavha, matn, versiya | B1 |

### 7.3. O'quv jarayoni

| Model | Asosiy maydonlar | Bosqich |
|---|---|---|
| `Enrollment` | userId, courseId, status, source (PAYMENT, MANUAL, FREE; SUBSCRIPTION va B2B — B2), studyFormat (ONLINE/OFFLINE), expiresAt? (offlayn oylik to'lov uchun) | B1 |
| `LessonProgress` | userId, lessonId, positionSec, watchedSec, completedAt | B1 |
| `StudyActivity` | userId, sana, daqiqalar (streak va grafiklar uchun) | B2 |
| `Note` | userId, lessonId, videoSec, matn | B2 |
| `StudyPlan` / `StudyPlanItem` | AI tuzgan reja | B2 |

### 7.4. Baholash

| Model | Asosiy maydonlar | Bosqich |
|---|---|---|
| `Quiz` | lessonId yoki courseId (yakuniy), sozlamalar (o'tish bali, vaqt, urinishlar, aralashtirish) | B2 |
| `Question` | quizId, turi, matn, variantlar, to'g'ri javob, tushuntirish, ball | B2 |
| `CodeTestCase` | questionId, input, expectedOutput, isHidden | B2 |
| `QuizAttempt` | userId, quizId, boshlanish/tugash vaqti, ball, passed | B2 |
| `AttemptAnswer` | attemptId, questionId, javob, isCorrect, aiExplanation | B2 |
| `ProjectAssignment` | moduleId, tavsif, rubrika, muddat, maxResubmits | B2 |
| `ProjectSubmission` | userId, assignmentId, githubUrl, fileKey, holat, baho, versiya | B2 |
| `SubmissionReview` | submissionId, reviewer (AI yoki instruktor), izohlar, audio/video feedback | B2 |
| `SimilarityReport` | submissionId, o'xshash topshiriq, foiz | B2 |
| `Certificate` | userId, courseId, code, ball, issuedAt, revokedAt, sabab | B2 |

### 7.5. To'lovlar

| Model | Asosiy maydonlar | Bosqich |
|---|---|---|
| `Order` | userId, turi (COURSE, BUNDLE, SUBSCRIPTION), itemId, amount, discount, promoCodeId, status, provider | B1 |
| `PaymentTransaction` | orderId, provider, providerTransId, status, fiscalReceiptUrl | B1 |
| `PaymentLog` | provider, action, request, response | B1 |
| `Refund` | orderId, summa, sabab, holat, kim tasdiqlagan | B1 (qo'lda) / B2 |
| `Plan` | obuna rejalari: narx, davr, qaysi kurslar | B2 |
| `Subscription` | userId, planId, holat, currentPeriodEnd, cardToken (shifrlangan) | B2 |
| `PromoCode` / `PromoRedemption` | kod, chegirma, cheklovlar | B2 |
| `Bundle` | kurslar to'plami | B2 |

### 7.6. Muloqot va qo'llab-quvvatlash

| Model | Asosiy maydonlar | Bosqich |
|---|---|---|
| `Lead` | ism, telefon, kurs, holat, menejer, izoh, utm | B1 |
| `AIConversation` / `AIMessage` | userId, kontekst (lessonId), rol, matn, tokenlar, baho | B2 |
| `AIUsage` | userId, sana, tokenlar, xarajat | B2 |
| `LessonQuestion` / `LessonAnswer` | dars ostidagi savol-javob | B2 |
| `ForumThread` / `ForumPost` | forum | B3 |
| `Review` | kurs sharhi, yulduz, javob | B2 |
| `SupportTicket` / `TicketMessage` | kategoriya, holat, ustuvorlik, operator | B3 |
| `Notification` | userId, turi, kanal, holat, o'qilgan | B2 |
| `NotificationPreference` | userId, kanal, turi, yoqilgan | B2 |
| `Badge` / `UserBadge` | nishonlar | B3 |
| `Report` | shikoyatlar (moderatsiya) | B3 |
| `AuditLog` | django-auditlog: actor, action, obyekt, o'zgargan maydonlar (eski → yangi) | B1 |

---

## 8. API tuzilmasi

**Umumiy qoidalar:**
- Barcha API backend'da (Django REST Framework), REST, prefiks `/api/v1/`. Quyidagi jadvalda prefiks qisqartirilgan: `/api/leads` = `/api/v1/leads/`.
- Hujjat: Swagger `/api/docs/` (faqat dev va staging'da ochiq).
- Autentifikatsiya: session cookie; o'zgartiruvchi so'rovlar (`POST`, `PUT`, `PATCH`, `DELETE`) `X-CSRFToken` header bilan. Tashqi webhook'lar (Click, Telegram) CSRF'dan ozod, o'rniga imzo tekshiriladi.
- Barcha kiruvchi ma'lumotlar DRF serializer'lari bilan tekshiriladi. Frontend formalarida qo'shimcha Zod validatsiyasi.
- Xatolar yagona formatda qaytadi: `{ error: { code, message } }`.
- Har bir endpoint **rol va egalikni** serverda tekshiradi.

| Yo'nalish | Vazifasi | Bosqich |
|---|---|---|
| `/api/auth/*` | OTP, ro'yxatdan o'tish, kirish, refresh, chiqish, parolni tiklash | B1 |
| `/api/leads` | Ariza | B1 |
| `/api/courses`, `/api/paths` | Katalog, qidiruv | B1 / B2 |
| `/api/lessons/[id]/playback`, `/key` | Imzolangan HLS URL, AES kaliti | B1 |
| `/api/progress` | Progress | B1 |
| `/api/uploads/presign` | Multipart yuklash | B1 |
| `/api/orders` | Buyurtma yaratish | B1 |
| `/api/payments/click/{prepare,complete}` | Click webhook | B1 |
| `/api/payments/payme` | Payme JSON-RPC | B2 |
| `/api/payments/uzum/*` | Uzum | B2 |
| `/api/quizzes/*` | Test boshlash, javob saqlash, yakunlash | B2 |
| `/api/code/run` | Kodni sandbox'da ishga tushirish (rate limit bilan) | B2 |
| `/api/projects/*` | Topshirish, baholash | B2 |
| `/api/ai/chat` | AI chat (SSE streaming) | B2 |
| `/api/ai/plan` | O'quv reja | B2 |
| `/api/certificates/*`, `/api/verify/[code]` | Sertifikatlar | B2 |
| `/api/notifications/*` | Bildirishnomalar | B2 |
| `/api/telegram/webhook` | Telegram bot | B2 |
| `/api/support/*` | Ticketlar, jonli chat | B3 |
| `/api/forum/*`, `/api/reviews/*` | Forum, sharhlar | B2 / B3 |
| `/api/analytics/*` | Hisobotlar | B2 / B3 |

---

## 9. Tashqi integratsiyalar

| Xizmat | Vazifasi | Muhim talablar | Bosqich |
|---|---|---|---|
| **Click** | To'lov | SHOP API (Prepare/Complete), MD5 imzo, idempotentlik, fiskalizatsiya. Obuna uchun karta tokenizatsiyasi (Merchant API) | B1 / B2 |
| **Payme** | To'lov | Merchant API (JSON-RPC), Basic auth, tranzaksiya holatlari, fiskal ma'lumotlar | B2 |
| **Uzum** | To'lov | Rasmiy hujjat bo'yicha | B2 |
| **Eskiz.uz** | SMS | SMS shablonlarini oldindan tasdiqlatish, token yangilash | B1 |
| **Telegram Bot API** | Arizalar, ogohlantirishlar, foydalanuvchi boti, login, jonli support | Webhook, bot foydalanuvchini akkauntga bog'lash (deep link) | B1 / B2 / B3 |
| **Anthropic API** | AI | Streaming, prompt caching, limitlar, xatolarda qayta urinish | B2 |
| **Judge0** (self-hosted) | Kodni ishga tushirish | Alohida serverda, tarmoqsiz; CPU/xotira/vaqt limitlari | B2 |
| **ClamAV** | Fayllarni antivirus tekshiruvi | Barcha yuklangan talaba fayllari | B2 |
| **Object storage** | Fayllar | Presigned URL, versiyalash, lifecycle (raw videolarni arxivlash) | B1 |
| **ASR** (masalan, Whisper) | Subtitr va transkript qoralamasi | O'zbek tili sifati sinab ko'riladi, inson tahriri majburiy | B2 (transkript) / B3 |
| **Sentry** | Xatolar | Frontend + backend + worker'lar | B1 |
| **GA4 / Yandex Metrika** | Analitika | Cookie roziligi bilan | B1 |
| **GitHub API** | Loyiha repozitoriyasini olish | Faqat ommaviy repo yoki GitHub App orqali | B2 |

> Har bir integratsiya uchun aniq protokol (imzo formulasi, xato kodlari) ish boshlanishidan oldin provayderning **rasmiy hujjati** bo'yicha tekshiriladi.

---

## 10. Xavfsizlik

**Transport va headerlar:**
- Faqat HTTPS (TLS 1.2+), HSTS.
- CSP, X-Frame-Options, Referrer-Policy, Permissions-Policy.

**Autentifikatsiya:**
- Parollar argon2 bilan hash qilinadi.
- Django session: cookie httpOnly, `Secure`, `SameSite=Lax`; sessiyalar Redis'da saqlanadi.
- CSRF himoyasi: o'zgartiruvchi so'rovlar `X-CSRFToken` header bilan yuboriladi.
- Parol o'zgarganda boshqa barcha sessiyalar avtomatik bekor bo'ladi (Django session auth hash).
- Django Admin'ga faqat xodimlar kiradi; login uchun rate limit.
- Xodim rollari (Admin, Instruktor, Manager, Support) uchun 2FA (django-otp, TOTP) **[B2]**.

**Avtorizatsiya:**
- Har bir so'rovda rol va egalik serverda tekshiriladi.
- **Rol va egalik testlari** avtomatik test to'plamida bo'lishi shart.

**Rate limiting:**
- Login, OTP, ariza, AI, kod ishga tushirish, to'lov endpointlari.
- Umumiy IP limiti.
- DDoS'dan himoya provayder yoki CDN darajasida.

**Kiruvchi ma'lumotlar:**
- DRF serializer validatsiyasi (frontend'da qo'shimcha Zod).
- Django ORM parametrlangan so'rovlari; xom SQL faqat parametrlar bilan.
- Admin yozgan HTML (kurs tavsifi, huquqiy sahifalar) saqlashda serverda tozalanadi (nh3, ruxsat etilgan teglar ro'yxati). Frontend faqat shu tozalangan HTML'ni ko'rsatadi; foydalanuvchi yozgan matn HTML sifatida emas, oddiy matn sifatida chiqariladi.

**Fayllar:**
- Tur fayl tarkibi bo'yicha tekshiriladi, hajm cheklanadi.
- Antivirus tekshiruvi.
- Zip-bomb'dan himoya.
- Fayllar alohida domen yoki bucket'dan beriladi.
- Yuklangan fayllar hech qachon serverda bajarilmaydi.

**Video:** imzolangan URL, AES, watermark.

**To'lovlar:** imzo, summa, idempotentlik, loglash, IP whitelist (provayder qo'llasa).

**Kod sandbox'i:**
- Alohida server, tarmoqqa chiqish yo'q.
- Resurs limitlari.
- Asosiy DB'ga kirish yo'q.

**AI:**
- Prompt injection'dan himoya (4.9-bo'lim).
- AI'ga shaxsiy ma'lumot yuborilmaydi.
- Limitlar.

**Maxfiy kalitlar:**
- Faqat muhit o'zgaruvchilarida yoki secret manager'da.
- Karta tokenlari shifrlangan holda saqlanadi.

**Audit va zaifliklar:**
- Muhim amallar audit log'ga yoziladi.
- Bog'liqliklar zaifligi CI'da tekshiriladi (`npm audit`, `pip-audit`, Dependabot).
- Production'ga chiqishdan oldin mustaqil pentest **[B1 oxiri, har yili]**.

---

## 11. Huquqiy talablar

**Shaxsiy ma'lumotlar:**
- O'zbekiston fuqarolarining shaxsiy ma'lumotlari **O'zbekiston hududidagi serverlarda** saqlanadi (lokalizatsiya talabi).
- Shaxsiy ma'lumotlar bazasini ro'yxatdan o'tkazish talablari yurist bilan tekshiriladi.

**Rozilik:**
- Oferta, maxfiylik siyosati va marketing uchun alohida rozilik; versiya va sana saqlanadi.
- Accessibility ma'lumotlari uchun alohida rozilik.

**Xorijga uzatish:** AI (Anthropic) va boshqa xorijiy xizmatlarga faqat anonimlashtirilgan o'quv kontenti va talaba savollari yuboriladi. Bu maxfiylik siyosatida yoziladi.

**Fiskalizatsiya:** har bir to'lov uchun fiskal chek, har bir kurs uchun MXIK kodi.

**Huquqiy hujjatlar** (yurist tayyorlaydi): ommaviy oferta, maxfiylik siyosati, refund qoidalari, foydalanish qoidalari, instruktorlar bilan shartnoma.

**Litsenziya va sertifikat maqomi:** ta'lim faoliyati uchun litsenziya kerakmi va sertifikatning huquqiy maqomi yurist bilan aniqlanadi. Sertifikatda "davlat namunasidagi hujjat emas" degan izoh bo'lishi mumkin.

**Mualliflik huquqi:** kurs videolari va materiallariga huquqlar instruktor shartnomasida belgilanadi.

**Akkauntni o'chirish:** foydalanuvchi so'roviga ko'ra 30 kun ichida. Moliyaviy yozuvlar qonunda belgilangan muddat davomida saqlanadi.

---

## 12. Nofunksional talablar

| Talab | Qiymat |
|---|---|
| **Tezlik (landing, katalog)** | LCP < 2.5s (mobil 4G), CLS < 0.1, INP < 200ms |
| **Lighthouse** | Performance ≥ 85, SEO ≥ 95, Best Practices ≥ 95. Accessibility: ≥ 90 (B1–B2), ≥ 95 (B3) |
| **API** | p95 < 300ms (AI va video'dan tashqari) |
| **AI** | Birinchi token < 3s |
| **Video** | Boshlanish < 3s; 1.5 Mbit/s'da 480p uzluksiz |
| **Yuklama** | B1: 300 ta bir vaqtdagi foydalanuvchi; B3: 1000+ (yuklama testi bilan tasdiqlanadi) |
| **Uptime** | 99.5% (oyiga ≤ 3.6 soat uzilish) |
| **Backup** | RPO ≤ 24 soat (B1), ≤ 1 soat (B3, WAL arxivi); RTO ≤ 4 soat |
| **Brauzerlar** | Chrome, Edge, Firefox, Safari — oxirgi 2 versiya; iOS 16+, Android 10+ |
| **Ekranlar** | 320px — 2560px, mobile-first |
| **Accessibility** | B1–B2: asosiy talablar (4.21-bo'lim boshidagi eslatma); B3: WCAG 2.1 AA |
| **Kod sifati** | Frontend: TypeScript strict, 0 ta `any`, ESLint va Prettier. Backend: ruff (lint + format), mypy. Hammasi CI'da |
| **Test qamrovi** | Biznes mantiq (to'lov, ruxsat, baholash) ≥ 80% |
| **Loglar** | Tuzilgan JSON loglar; shaxsiy ma'lumot va kalitlar logga yozilmaydi |

---

## 13. Infratuzilma va deploy

**Muhitlar:**
- `local` — Docker Compose: `docker compose up` (`docker-compose.yml` + avtomatik ulanadigan `docker-compose.override.yml`, hot reload).
- `staging` — to'lov tizimlari test rejimida, test ma'lumotlari.
- `production` — Docker Compose: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`.

**Docker servislari:**

| Servis | Image | Vazifasi |
|---|---|---|
| `nginx` | nginx:alpine | Reverse proxy, TLS, static fayllar, security headerlar, HLS kesh |
| `frontend` | `./frontend/Dockerfile` (Next.js standalone) | SSR |
| `backend` | `./backend/Dockerfile` | Django: REST API + admin (gunicorn + uvicorn); ishga tushishda `migrate` |
| `worker` | `./backend/Dockerfile` (boshqa buyruq) | Celery: xabarlar va fon vazifalari |
| `worker-video` | `./backend/Dockerfile` (`video` target, ffmpeg bilan) | Celery: video → HLS |
| `beat` | `./backend/Dockerfile` (boshqa buyruq) | Celery beat: davriy vazifalar |
| `postgres` | pgvector/pgvector:pg17 | DB |
| `redis` | redis:7-alpine | Celery broker, kesh, sessiyalar, rate limit |
| `seaweedfs` | chrislusf/seaweedfs | Faqat dev: S3-mos storage |

- Multi-stage build, runtime'da root bo'lmagan foydalanuvchi, har bir servisda `healthcheck`.
- Maxfiy kalitlar image ichiga kirmaydi — faqat `.env` / secret orqali.

**Hosting:** O'zbekistondagi data-markaz yoki bulut provayder (11-bo'limga ko'ra).

**Boshlang'ich production konfiguratsiyasi:**

| Server | Vazifasi |
|---|---|
| App server | nginx, frontend, backend, Celery worker'lar va beat (Docker Compose) |
| DB server | PostgreSQL + kunlik backup boshqa joyga |
| Object storage | Videolar va fayllar |
| Sandbox server | Judge0 (B2'dan) |

**Kengayish:**
- Frontend, backend va worker gorizontal ko'paytiriladi (stateless).
- Video worker'lar alohida serverga chiqariladi.
- CDN ulanadi.

**CI/CD** (frontend va backend uchun alohida workflow):
- PR'da: lint → typecheck → unit testlar → Docker build → E2E (staging'da).
- `main` → Docker image registry'ga → staging'ga avtomatik deploy.
- Production'ga qo'lda tasdiqlash bilan chiqariladi.

**Migratsiyalar:** Django migrations. Faqat orqaga mos o'zgarishlar; buzuvchi o'zgarishlar ikki bosqichda qilinadi.

**Monitoring:**
- Sentry (xatolar).
- Uptime monitor.
- Server metrikalari.
- Biznes ogohlantirishlari Telegram'ga: to'lov xatolari, AI budjeti, video qayta ishlash xatolari.

**Backup:**
- Kunlik to'liq backup, 30 kun saqlanadi.
- Har oy tiklash sinovi.
- Object storage'da versiyalash.

---

## 14. Sifatni ta'minlash va testlash

### 14.1. Testlar turlari

| Tur | Vosita | Nima tekshiriladi |
|---|---|---|
| Unit | pytest (backend), Vitest (frontend) | Servislar: narx va chegirma hisoblash, test baholash, ruxsatlar, imzo tekshiruvi |
| Integratsion | pytest-django + test DB | To'lov webhook'lari (barcha holatlar), enrollment yaratish, progress |
| E2E | Playwright | Asosiy yo'llar: ro'yxatdan o'tish → to'lov → dars → test → sertifikat |
| Accessibility | axe-core (CI'da), qo'lda ekran o'quvchi bilan | B1'dan avtomatik, B3'da to'liq audit |
| Yuklama | k6 | Katalog, dars sahifasi, to'lov, AI |
| Xavfsizlik | OWASP ZAP, mustaqil pentest | B1 oxiri va har yili |
| AI sifati | Eval to'plami | 4.9-bo'lim |

### 14.2. Jarayon

- Har bir PR: code review + CI yashil bo'lishi shart.
- Har bir sprint oxirida staging'da demo va qabul qilish.

### 14.3. Xatolar ustuvorligi

| Daraja | Tavsif | Tuzatish muddati |
|---|---|---|
| **P0** | To'lov, kirish yoki ma'lumot yo'qolishi | 4 soat |
| **P1** | Asosiy funksiya ishlamaydi | 2 kun |
| **P2** | Boshqa xatolar | Keyingi sprint |

### 14.4. Mahsulot analitikasi (hodisalar)

`lead_submit`, `signup_complete`, `course_view`, `checkout_start`, `payment_success`, `lesson_start`, `lesson_complete`, `quiz_submit`, `project_submit`, `ai_message`, `certificate_issued`, `subscription_start`, `subscription_cancel`.

---

## 15. Rivojlantirish bosqichlari (yo'l xaritasi)

### Bosqich 1 — MVP: sotish va o'qitish (8 hafta)

**Qamrov:**
- Landing (3D), ariza formasi va Telegram xabarnoma.
- 3 til.
- Telefon orqali autentifikatsiya.
- Katalog va kurs sahifasi.
- Video pipeline va himoya.
- Dars sahifasi va progress.
- Click (bir martalik to'lov) va fiskalizatsiya.
- Admin panel (Django Admin) va audit log.
- Huquqiy sahifalar, Sentry, backup.

| Sprint | Haftalar | Natija |
|---|---|---|
| 0 | 1 (parallel) | Brend (logo SVG), dizayn tizimi va 3D konsepsiya |
| 1 | 1–2 | Frontend va backend loyihalari, Docker Compose, CI, i18n, **3D landing + arizalar** (alohida ishga tushirish mumkin) |
| 2 | 3–4 | Auth, kurslar admin'da, katalog, kurs sahifasi |
| 3 | 5–6 | Video pipeline, pleyer, dars sahifasi, progress |
| 4 | 7–8 | Click, checkout, admin to'lovlar, E2E testlar, pentest, production |

> Batafsil ish rejasi: `PLAN.md`.

### Bosqich 2 — O'quv sifati va AI (10–12 hafta)

**Qamrov:**
- Testlar (kod savollari va Judge0 bilan) va loyiha topshirish (AI review, o'xshashlik tekshiruvi).
- AI yordamchi (RAG, limitlar, o'quv reja).
- Sertifikatlar va ularni tekshirish.
- Instruktor va Manager panellari.
- Payme, Uzum, obuna, promo-kodlar, bundle'lar, avtomatik refund.
- Telegram bot (bildirishnomalar va support).
- Bildirishnomalar (ichki, Telegram, email).
- Streak va maqsadlar, dars savol-javoblari, sharhlar, portfolio.
- O'quv yo'llari, transkriptlar, xodimlar uchun 2FA.

| Sprint | Natija |
|---|---|
| 5–6 | Testlar tizimi (MCQ, kod savollari va Judge0), instruktor paneli |
| 7–8 | Loyiha topshirish, AI review, o'xshashlik tekshiruvi, baholash navbati |
| 9–10 | AI yordamchi (RAG, chat, xatolarni tushuntirish, o'quv reja), sertifikatlar |
| 11–12 | Payme, Uzum, obuna, promo-kodlar, Manager paneli, bildirishnomalar, Telegram bot |

### Bosqich 3 — Inklyuzivlik va qo'llab-quvvatlash (10 hafta)

**Qamrov:**
- WCAG 2.1 AA va accessibility sozlamalari.
- Subtitlar (ASR + tahrir) va transkriptlar.
- O'IT overlay pleyer, sinxronizatsiya va burn-in.
- IT atamalarining O'IT lug'ati.
- Maxsus profil, soddalashtirilgan AI rejimi.
- Support: AI bot, ticketlar, jonli operator.
- Forum, nishonlar va XP, skill map.
- Analitika dashboardi, web push.
- Mustaqil WCAG auditi.

| Sprint | Natija |
|---|---|
| 13–14 | WCAG auditi va tuzatishlar, accessibility sozlamalari, subtitlar |
| 15–16 | O'IT pleyer, sinxronizatsiya, burn-in, O'IT lug'ati |
| 17–18 | Support tizimi (bot, ticketlar, jonli chat) |
| 19–20 | Forum, gamifikatsiya, analitika, mustaqil audit |

> **Muhim:** O'IT videolarini yozish (tarjimonlar, studiya) 3-bosqich boshlanishidan **oldin** boshlanishi kerak. Bu dasturlashdan ko'ra uzoqroq davom etadigan ish.

### Backlog (bosqichga kiritilmagan)

Faqat 1–3-bosqichlar tugagach va biznes ehtiyoj tasdiqlansa ko'riladi: mobil ilova, B2B guruh litsenziyalari, instruktorlar marketplace'i, blog.

---

## 16. Qabul qilish mezonlari

### Bosqich 1

- [ ] `docker compose up` bilan barcha servislar (frontend, backend, Celery worker'lar va beat, DB, Redis, storage, nginx) ishga tushadi va `healthy` holatda.
- [ ] Landing 3 tilda; arizalar 10 soniya ichida Telegram'ga va admin panelga tushadi.
- [ ] 3D hero 12-bo'lim tezlik talablarini buzmaydi; `prefers-reduced-motion` va WebGL'siz qurilmada statik variant chiqadi.
- [ ] Ro'yxatdan o'tish, SMS, kirish va parolni tiklash ishlaydi.
- [ ] Admin kurs yaratadi, video `READY` bo'ladi.
- [ ] Sotib olinmagan kurs videosini to'g'ridan-to'g'ri URL orqali ochib bo'lmaydi.
- [ ] Click test muhitida barcha holatlar o'tadi: muvaffaqiyat, noto'g'ri imzo, noto'g'ri summa, takroriy so'rov, bekor qilish.
- [ ] To'lovdan keyin kurs avtomatik ochiladi; fiskal chek yaratiladi.
- [ ] Rol va egalik testlari o'tadi; pentest'dagi kritik va yuqori xatolar yopilgan.
- [ ] 12-bo'limdagi tezlik, brauzer va ekran talablari bajarilgan.

### Bosqich 2

- [ ] Barcha savol turlari, jumladan kod savollari (sandbox'da), to'g'ri baholanadi; test paytida AI o'chirilgan.
- [ ] Loyiha: topshirish → AI review (≤ 5 daqiqa) → o'xshashlik hisoboti → instruktor bahosi → qayta topshirish.
- [ ] AI 3 tilda javob beradi; eval to'plamida ≥ 85% javob "to'g'ri va foydali" deb baholangan; limitlar ishlaydi.
- [ ] Sertifikat avtomatik beriladi va `/verify` orqali tekshiriladi.
- [ ] Payme va obuna (avtomatik yangilanish bilan) test muhitida o'tadi; promo-kodlar ishlaydi.
- [ ] Instruktor va Manager faqat o'z ruxsatlari doirasidagi ma'lumotlarni ko'radi.

### Bosqich 3

- [ ] Mustaqil WCAG 2.1 AA auditi muvaffaqiyatli o'tgan; Lighthouse Accessibility ≥ 95.
- [ ] O'IT overlay Chrome, Firefox, Edge va desktop Safari'da sinxron ishlaydi (farq ≤ 0.3s); iOS'da burn-in versiya ishlaydi.
- [ ] Subtitlar 3 tilda, sozlanadi, O'IT bilan birga yoqiladi.
- [ ] Ekran o'quvchilar bilan asosiy yo'llar (ro'yxatdan o'tish → to'lov → dars → test) to'liq o'tiladi.
- [ ] Support: bot, ticketlar va jonli chat ishlaydi; SLA hisoboti chiqadi.
- [ ] Kar va ko'zi ojiz foydalanuvchilar ishtirokida kamida 5 kishilik usability test o'tkazilgan.

---

## 17. Xavflar

| Xavf | Ehtimol | Ta'sir | Kamaytirish choralari |
|---|---|---|---|
| Kontent (videolar) o'z vaqtida tayyor bo'lmaydi | Yuqori | Yuqori | Kontent rejasi dasturlash bilan parallel; ishga tushirish uchun 2–3 kurs yetarli |
| Click shartnomasi va fiskalizatsiya kechikadi | O'rta | Yuqori | 1-sprintdayoq boshlash; vaqtincha qo'lda kirish berish |
| Video trafik va saqlash xarajati oshib ketadi | O'rta | O'rta | Adaptive bitrate, CDN, eski raw fayllarni arxivlash, xarajat monitoringi |
| AI xarajati nazoratdan chiqadi | O'rta | O'rta | Limitlar, kesh, arzon model oddiy vazifalar uchun, budjet ogohlantirishi |
| AI o'zbek tilida sifatsiz javob beradi | O'rta | O'rta | Eval to'plami, RAG, 👍/👎 monitoringi |
| O'IT tarjimonlari yetishmaydi, atamalar yagona emas | Yuqori | Yuqori | Tarjimonlar uyushmasi bilan erta hamkorlik, O'IT lug'ati |
| Videolar qaroqchilarcha tarqatiladi | O'rta | O'rta | AES, imzolangan URL, watermark, qonuniy choralar |
| Qamrov kengayib ketadi (scope creep) | Yuqori | Yuqori | Bosqichlarga qat'iy rioya; yangi g'oyalar backlog'ga |
| Kichik jamoa, bitta odamga bog'liqlik | O'rta | Yuqori | Hujjatlashtirish, code review, CI |
| 3D landing sekin qurilmalarda sekin ishlaydi | O'rta | O'rta | Lazy yuklash, statik poster, `PerformanceMonitor`, mobil uchun soddalashtirilgan sahna, bundle budjeti |

---

## 18. Ochiq masalalar

| # | Masala | Kim hal qiladi | Muddat |
|---|---|---|---|
| 1 | Yuridik shaxs, Click / Payme merchant shartnomalari | Buyurtmachi | B1, Sprint 3 gacha |
| 2 | Fiskalizatsiya usuli va MXIK kodlari | Buxgalter | B1, Sprint 4 gacha |
| 3 | Oferta, maxfiylik siyosati, refund qoidalari, instruktor shartnomasi | Yurist | B1 oxirigacha |
| 4 | Ta'lim litsenziyasi va sertifikat maqomi | Yurist | B2 gacha |
| 5 | Domen, hosting provayderi (O'zbekistonda) | Buyurtmachi | B1, Sprint 1 |
| 6 | Kurslar ro'yxati, narxlari, instruktorlar, video tayyorlash jadvali | Buyurtmachi | B1, Sprint 2 |
| 7 | Brend: logoning vektor fayli (hozir faqat JPG), matnlar | Buyurtmachi | Sprint 0 |
| 8 | Obuna rejalari va narxlari | Buyurtmachi | B2 boshi |
| 9 | AI uchun oylik budjet va har bir talaba uchun limitlar | Buyurtmachi | B2 boshi |
| 10 | O'IT tarjimonlari va studiya, kar hamjamiyati bilan hamkorlik | Buyurtmachi | B2 davomida (B3 dan oldin) |
| 11 | Instruktorlar bilan ishlash modeli (xodim, shartnoma yoki daromad ulushi) | Buyurtmachi | B2 boshi |

---

## 19. Muhit o'zgaruvchilari

Har bir loyihaning o'z `.env` fayli bor. Root'dagi `.env` faqat Docker Compose uchun (DB paroli, dev S3 kalitlari, portlar).

### `frontend/.env`

```env
NEXT_PUBLIC_APP_URL=
API_INTERNAL_URL=http://backend:8000   # SSR uchun (Docker tarmog'i ichida)
NEXT_PUBLIC_SENTRY_DSN=
NEXT_PUBLIC_GA_ID=
```

### `backend/.env`

```env
# Django
DJANGO_SETTINGS_MODULE=config.settings.prod
DJANGO_SECRET_KEY=
DJANGO_ALLOWED_HOSTS=
DJANGO_CSRF_TRUSTED_ORIGINS=
APP_URL=

# DB / Redis
DATABASE_URL=
REDIS_URL=
CELERY_BROKER_URL=

# Storage
S3_ENDPOINT=                # backend ichidan (masalan, http://seaweedfs:8333)
S3_PUBLIC_ENDPOINT=         # brauzer uchun (presigned URL'lar)
S3_REGION=
S3_BUCKET_PRIVATE=          # videolar, materiallar
S3_BUCKET_PUBLIC=           # rasmlar (kurs muqovasi, avatar)
S3_ACCESS_KEY=
S3_SECRET_KEY=
MAX_VIDEO_SIZE_MB=2048
MAX_PROJECT_ZIP_MB=50
HLS_SIGNED_URL_TTL_SEC=7200

# SMS
ESKIZ_EMAIL=
ESKIZ_PASSWORD=
SMS_DRY_RUN=true

# Payments
CLICK_SERVICE_ID=
CLICK_MERCHANT_ID=
CLICK_MERCHANT_USER_ID=
CLICK_SECRET_KEY=
PAYME_MERCHANT_ID=          # B2
PAYME_SECRET_KEY=           # B2
UZUM_*=                     # B2

# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_LEADS_CHAT_ID=
TELEGRAM_ALERTS_CHAT_ID=

# OAuth (B2)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# AI (B2)
ANTHROPIC_API_KEY=
AI_MODEL_MAIN=              # murakkab vazifalar (chat, review)
AI_MODEL_FAST=              # oddiy vazifalar
AI_DAILY_MESSAGE_LIMIT=50
AI_MONTHLY_BUDGET_USD=

# Code sandbox (B2)
JUDGE0_URL=
JUDGE0_API_KEY=

# Monitoring
SENTRY_DSN=
```

---

*Sifat Edu — har bir o'quvchi uchun, imkoniyatidan qat'i nazar.*
