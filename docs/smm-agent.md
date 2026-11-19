# SMM agent: Instagram va Telegram uchun avtomatik kontent

**Holat:** 1-bosqich tayyor (2026-11-19) — `backend/apps/smm`. Formulalar raqobatchilar tahlilidan olingan: `docs/raqobatchilar-tahlili.md`.

## Ishga tushirish (1-bosqich)

1. Markaz botini Telegram kanalga (@sifatedu) **administrator** qilib qo'shing (xabar yuborish huquqi bilan).
2. Admin → SMM agent → SMM sozlamalari:
   - **Telegram kanal:** `@sifatedu`;
   - **chiqish soati:** 19;
   - **markaz haqida faktlar:** natijalar, yangiliklar, chegirmalar, manzil, telefon — har qatorda bitta. Agent faqat shu faktlar va kurslar ro'yxatidan foydalanadi, raqam o'ylab topmaydi.
   - «yoqilgan» belgisini qo'ying.
3. Tasdiqlovchilar — Admin roli bor va Telegram'i saytdagi akkauntiga ulangan xodimlar. Menejerga ham tasdiqlash huquqi beriladi.
4. Birinchi rejani darhol tuzish: SMM sozlamalari ro'yxatida qatorni belgilab, «Keyingi hafta rejasini tuzish» amalini bajaring. Keyin Postlar ro'yxatida kerakli postlarni belgilab, «Hozir tayyorlash» ni bosing.

5. **Kuchliroq AI (ixtiyoriy, tavsiya).** Serverdagi `backend/.env` ga yozing:

   ```
   SMM_GEMINI_MODEL=<AI Studio'dagi Pro model nomi, aynan>
   SMM_GEMINI_PRICE_INPUT=<1M token narxi, $>
   SMM_GEMINI_PRICE_OUTPUT=<1M token narxi, $>
   ```

   Keyin `deploy.sh` ni ishga tushiring. Bo'sh qolsa, umumiy `GEMINI_MODEL` ishlatiladi. API kaliti o'sha `GEMINI_API_KEY` bo'ladi. Gemini ilovasidagi «Pro» obunasi API'ga tegishli emas: API alohida, ishlatilgan token bo'yicha to'lanadi.

Keyin hammasi o'zi ishlaydi:
- **yakshanba 10:00** — keyingi hafta rejasi;
- **har soatda** — chiqishiga 30 soat qolgan postlar tayyorlanib, botga tasdiqqa keladi;
- **har 10 daqiqada** — vaqti kelgan tasdiqlangan postlar kanalga chiqadi.

Chiqish vaqtidan 2 soat o'tgach ham tasdiqlanmagan post bekor bo'ladi.

**Hafta:**
- Dushanba: oilaviy mini-sahna ssenariysi (suratga olish uchun) + karusel «foydali»;
- Seshanba: rasm «ota-onaga savol»;
- Chorshanba: rasm «IT hazili»;
- Payshanba: «haqiqiy natija» ssenariysi + karusel «IT ichidan»;
- Juma: karusel «hikoya»;
- Shanba: karusel «foydali»;
- Yakshanba: rasm «ota-onaga savol».

Ssenariylar kanalga chiqmaydi: ular markaz telefonda suratga olishi uchun yuboriladi.

## Qaror qilinganlar

- **Chiqarish tartibi.** Agent kontentni o'zi yasaydi, lekin chiqarishdan oldin direktor Telegram'da tasdiqlaydi. Xabar ostida uchta tugma bo'ladi: «Chiqarish», «Qayta yasash», «Bekor». Keyinchalik sozlamada to'liq avtomat rejimini yoqish mumkin.
- **Jadval.** Kuniga 1 ta kontent:
  - haftada 3 ta reel: Dushanba — foydali, Chorshanba — hazil yoki taqqoslash, Juma — natija;
  - haftada 4 ta post: karusel yoki bitta rasm.

  Bir xil kontent ham Instagram'ga, ham Telegram kanalga chiqadi.
- **Uslub.** sifatedu.uz sayti uslubi: to'q fon, nuqtali to'r, oq sarlavha, qizil urg'u so'z. Yo'riqnoma va namunalar `brand/tools/muqovalar.py` da.
  - Odamlar, yuzlar va ikonkalar bo'lmaydi.
  - Videoda ovoz bo'ladi.
  - Kurs sotuvi faqat taklif sifatida beriladi, majburiy emas.
- **Joylashuv.** Backend ichida yangi `apps/smm` ilovasi bo'ladi. U Celery'da ishlaydi:
  - matn yozish `ai` navbatida;
  - video yasash `video` navbatida.

  Hozircha faqat Sifat Edu uchun (flagship) ishlaydi. Boshqa markazlar uchun keyin, SaaS tarifi orqali ochiladi.

## Qanday ishlaydi

1. **Haftalik reja (Yakshanba 10:00).**
   - Agent keyingi 7 kunlik mavzularni tuzadi.
   - Manbalar: saytdagi kurslar, markaz yangiliklari (siz yozib qo'yasiz), oldingi postlar statistikasi va takrorlanmaslik ro'yxati.
   - Matnni Gemini yozadi, chunki loyihada kalit allaqachon bor.
   - Har bir mavzu uchun ssenariy, ekrandagi matn, Instagram izohi, Telegram izohi va heshteglar tayyorlanadi.
2. **Yasash.** Chiqishdan bir kun oldin bajariladi.
   - **Post yoki karusel.** PIL shablonlari sayt uslubida chiziladi: 1080×1350, karuselda 3–7 slayd.
   - **Reel:**
     - ovozni Gemini TTS yozadi, bu AI Studio'dagi o'sha ovoz;
     - yonida o'zimiz sintez qilgan musiqa va effektlar bo'ladi;
     - kadrlarni PIL + ffmpeg yasaydi: so'zma-so'z subtitr, telefon/chat/kod oynalari, progress chiziq;
     - muqovasi ham shu uslubda.
   - Serverga brauzer o'rnatilmaydi, shuning uchun hammasi Python'da bo'ladi.
3. **Tasdiqlash.**
   - Bot tayyor fayl va ikkala izohni direktorga yuboradi.
   - Chiqish vaqti kelguncha tasdiqlanmagan kontent chiqmaydi va keyingi kunga ham surilmaydi.
4. **Chiqarish** (jadvaldagi vaqtda, masalan 19:00):
   - **Telegram:** kanalga markaz boti orqali chiqadi.
   - **Instagram:** rasmiy Instagram API orqali chiqadi. Fayl `media.sifatedu.uz` dagi ochiq havoladan olinadi.
5. **Statistika.**
   - 24 soatdan keyin Instagram'dan ko'rishlar, ulashishlar va saqlashlar olinadi.
   - Telegram'dan ko'rishlar olinadi.
   - Haftalik hisobot direktorga boradi. Eng yaxshi mavzular keyingi haftaning rejasiga ta'sir qiladi.

## Ma'lumotlar

- `SmmPost` modeli quyidagilarni saqlaydi:
  - turi: reel, post yoki karusel;
  - holati: rejada → yasalmoqda → tasdiq kutmoqda → tasdiqlandi → chiqdi, yoki xato / bekor;
  - mavzu, ssenariy (JSON), izohlar, fayllar (S3 storage), chiqish vaqti;
  - Instagram va Telegram ID'lari, statistika va AI xarajati.
- `SmmSettings` (singleton) saqlaydi:
  - yoqilgan yoki o'chiq;
  - avtomat rejim;
  - jadval;
  - Instagram tokeni (shifrlangan, `SecretField`);
  - Telegram kanal ID'si;
  - tasdiqlovchi chat.
- Admin'da: postlar ro'yxati, qo'lda mavzu qo'shish, «hozir yasash» tugmasi.

## Instagram'ni ulash (sizning qadamlaringiz)

Dastur orqali Instagram'ga post qo'yish uchun quyidagilar kerak:

1. **Professional hisob.** @sifatedu profilida «Statistika» tugmasi bor, demak hisob allaqachon professional (Business yoki Creator). Ilovada tekshirib qo'ying: Sozlamalar → Hisob turi.
2. **Meta ilovasi.**
   - developers.facebook.com'da ilova ochasiz. Uni men bosqichma-bosqich yo'riqnoma bilan yozib beraman.
   - Unga «Instagram API with Instagram Login» qo'shiladi va @sifatedu tester qilib biriktiriladi.
   - Shunda Facebook sahifa ham, Meta tekshiruvi (App Review) ham kerak bo'lmaydi, chunki ilova faqat o'z hisobimiz uchun ishlaydi.
3. **Token.** Tokenni siz serverda kiritasiz, chatga yozmaysiz. Agent uni har 50 kunda o'zi yangilab turadi.

Instagram ulanmaguncha agent faqat Telegram kanalga chiqaradi. Instagram uchun tayyor fayl va izohni sizga yuboradi, siz qo'lda qo'yasiz.

## Bosqichlar

1. **Asos.**
   - `apps/smm` modellari va admin;
   - Telegram'da tasdiqlash tugmalari;
   - Telegram kanalga chiqarish;
   - post va karusel shablonlari, Gemini bilan matn.
2. **Reels.**
   - Gemini TTS ovoz va musiqa;
   - PIL + ffmpeg video shablonlari: 3 xil format, har hafta almashib turadi;
   - muqova.
3. **Instagram API.** Meta ilovasi tayyor bo'lgach, chiqarish va token yangilash qo'shiladi.
4. **Statistika va o'rganish.** Insights, haftalik hisobot va reja uchun teskari aloqa.

Har bosqich testlar bilan alohida deploy qilinadi. Birinchi bosqichdan keyin agent darhol Telegram kanalda ishlay boshlaydi.

## Xavf va cheklovlar

- **Xato faktlar.** AI noto'g'ri fakt yozishi mumkin. Shuning uchun tasdiqlash qadami bor, va prompt faqat aniq ma'lumotlardan foydalanishni talab qiladi: kurslar va narxlar bazadan olinadi.
- **Video yasash.** Bitta reel taxminan 2–4 daqiqa CPU oladi va kuniga bitta yasaladi, umumiy serverga yuki kam.
- **Xarajat.** Gemini matn va TTS uchun oyiga taxminan $1–3.
- **Musiqa.** Mualliflik huquqi bor musiqa ishlatilmaydi, faqat o'zimiz sintez qilganimiz.
