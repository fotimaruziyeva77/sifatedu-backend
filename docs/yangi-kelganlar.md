# Yangi kelganlar yo'li: havola → daraja testi → kupon → menejer

Odam Instagram'dagi havoladan botga keladi, telefon raqamini yuborib ro'yxatdan o'tadi, bot
darhol yo'nalishlarni taklif qiladi. U qisqa vaqtli test ishlaydi va oxirida natijasini, darajasini
hamda chegirma kuponini oladi. Shu zahoti arizalar guruhiga ariza tushadi: menejer qo'ng'iroq
qiladi. Kuponning muddati tugashidan oldin bot ikki marta eslatadi.

## 1. Havolalar: kim qayerdan keldi

Har joyga o'z havolasini qo'ying — statistikada qaysi biri ko'proq odam olib kelgani ko'rinadi:

| Qayerga | Havola |
|---|---|
| Instagram profili (bio) | `https://t.me/sifat_edubot?start=ig` |
| Instagram reklamasi | `https://t.me/sifat_edubot?start=ig_ads` |
| Instagram storis | `https://t.me/sifat_edubot?start=ig_story` |
| Telegram kanal | `https://t.me/sifat_edubot?start=tg` |
| Flayer, banner (QR kod) | `https://t.me/sifat_edubot?start=flyer` |
| Ochiq dars, tadbir | `https://t.me/sifat_edubot?start=ochiq_dars` |

`start=` dan keyingi so'z — **manba**: kichik lotin harflari, raqamlar, `_` va `-`, 32 belgigacha.
O'zingiz istagancha yangisini o'ylab topasiz, kodga hech narsa qo'shish shart emas. Odamning
**birinchi** manbasi saqlanadi (keyin boshqa havoladan kirsa ham o'zgarmaydi). Do'st taklif
havolasi (`?start=r_KOD`) bilan kelganlar — `ref`.

Qayerda ko'rinadi:

* botdagi **«📊 Admin panel»** — «📍 Manbalar: ig 12 · tg 4 · ref 2 · to'g'ridan 3»;
* admin → **Foydalanuvchilar** → o'ngdagi filtr «manba»; foydalanuvchi sahifasida «Do'stni taklif
  qilish va manba»;
* admin → **Sotuv** → **Arizalar** → ariza ichida `utm_source`.

## 2. Botda nima bo'ladi

1. Odam havolani bosadi → «Start» → til → kanalga obuna → **«📱 Telefonni yuborish»**.
2. «Akkaunt ochildi» xabaridan keyin darhol: «🎯 Bepul daraja testi … 15% yoki 25% chegirma
   kuponi (72 soat)» va yo'nalish tugmalari (hozircha — **Python**).
3. Yo'nalish → shartlar (12 savol, 15 daqiqa, natija oxirida) → **«▶️ Boshlash»**. Vaqt shu
   tugma bilan boshlanadi va serverda hisoblanadi.
4. Savollar botning o'zida, tugmalar bilan. Javobdan keyin to'g'ri yoki noto'g'riligi
   aytilmaydi.
5. Oxirida: natija (%), daraja (boshlang'ich / o'rta / yaxshi), kupon va uning muddati,
   «🎁 Kuponni saytda ko'rish» tugmasi (parolsiz kiradi).

Shuningdek:

* **Kim ko'radi:** hali hech qaysi kursga yozilmaganlar. Menyuda «🎯 Daraja testi» tugmasi bor;
  kursga yozilgach yo'qoladi. Kursda o'qiyotgan o'quvchi test ham, kupon ham ololmaydi (aks holda
  keyingi oy to'loviga chegirma olib qo'yardi). Bosh admin (superuser) testni sinab ko'rish uchun
  ko'radi — unga ham kupon va ariza chiqadi, bu normal.
* **Qayta ishlash** mumkin (darajasini bilish uchun), lekin kupon faqat birinchi tugatilgan
  testga beriladi. Menyuda qayta bossa, bot uning kuponi va muddatini eslatadi.
* **Testni tashlab ketsa:** 15 daqiqa o'tgach test o'zi yopiladi (har 5 daqiqada tekshiriladi):
  javob bergan savollari hisoblanadi, kupon beriladi, botga xabar boradi va menejerga ariza
  tushadi — hech kim yo'qolmaydi.

## 3. Kupon

| Natija | Kupon | Muddat |
|---|---|---|
| 70% va undan yuqori | **25%** | 72 soat |
| 70% dan past | **15%** | 72 soat |

* Saytda kurs to'lovida **o'zi qo'llanadi** — kod kiritish shart emas. Bir nechta chegirma bo'lsa
  (do'st taklifi, boshqa kupon) — **eng kattasi**, ular qo'shilmaydi.
* Bitta kupon — bitta to'lovga. Offlayn guruhda bu — birinchi oy to'lovi.
* To'lovni boshlab, Click'da oxiriga yetkazmasa — kupon yo'qolmaydi, keyingi urinishda yana
  qo'llanadi. Muddati o'tgani qo'llanmaydi.
* Kabinetda: **Yutuqlar** sahifasining eng tepasida «Chegirma kuponlaringiz» — foiz, qayerdan
  kelgani, qachongacha va «Kursni tanlash».
* **Eslatmalar** (botga va saytdagi qo'ng'iroqchaga): 24 soatdan keyin — «kuponingiz kutyapti»;
  muddat tugashiga 12 soat qolganda — «kupon tugayapti». Kupon ishlatilsa yoki odam kursga
  yozilsa — yuborilmaydi.
* **Raqamlarni o'zgartirish:** admin → **XP va coin** → **Sozlamalar** → «Daraja testi (botga
  yangi kelganlar)»: chegara (70%), katta kupon (25%), kichik kupon (15%), muddat (72 soat).
* **Qo'lda kupon** (masalan, ochiq darsga kelganga): admin → **XP va coin** → **Kuponlar** →
  «Qo'shish»: egasi, foiz, «amal qiladi (gacha)». Muddatni bo'sh qoldirsangiz — muddatsiz.

## 4. Menejer uchun

Test tugashi bilan arizalar Telegram guruhiga va admin → **Sotuv** → **Arizalar**ga ariza
tushadi:

* manba — «Botdagi daraja testi», kurs — tanlangan yo'nalish;
* izohda: `Daraja testi (Python): 80%, kupon 25% (06.10 14:00 gacha), manba: ig`.

Bitta odamdan 24 soat ichida kelgan arizalar bittaga qo'shiladi (qayta ishlasa — izohga yangi
natija yoziladi). Barcha natijalar: admin → **Sotuv** → **Daraja testi natijalari**.

Qo'ng'iroqda: natija va darajani ayting, mos guruhni (vaqti, formati) taklif qiling va kupon
muddatini eslating — «kupon … gacha amal qiladi, to'lovda o'zi qo'llanadi».

## 5. Yangi yo'nalish qo'shish (masalan, Frontend)

1. Admin → **Kurslar** → «Daraja testlari (xizmat kursi)» → yangi modul va dars, masalan
   «Frontend: daraja testi» → darsga test va **«Tez kiritish»** bilan kamida 20 ta savol.
2. Admin → **Sotuv** → **Daraja testlari** → «Qo'shish»: nomi (botdagi tugma, masalan
   `Frontend`), yo'nalish — sotiladigan Frontend kursi, savollar — 1-banddagi test, 12 savol,
   15 daqiqa.
3. Tayyor: botdagi yo'nalishlar ro'yxatida yangi tugma chiqadi.

Xizmat kursini **nashr qilmang va unga hech kimni yozmang** — shunda savollar hech kimga
oldindan ko'rinmaydi va dars dasturiga aralashmaydi. Testni vaqtincha to'xtatish — «faol»
belgisini olib tashlang.

## 6. Serverda (bir marta)

Yangi versiyani chiqargach (`bash /srv/sifatedu/infra/deploy/deploy.sh`), Python savollari va
testini qo'shing:

```bash
cd /srv/sifatedu
S=backend/scripts/daraja_testi_python.py
dc exec -T -e ACTION=setup backend python manage.py shell < $S
```

Natijalar qisqacha — nechta odam ishladi, o'rtacha natija, kuponlar, manbalar, oxirgi 15 ta:

```bash
dc exec -T -e ACTION=status backend python manage.py shell < $S
```

Testni o'chirish va yoqish: `-e ACTION=off` / `-e ACTION=on`.

Sinab ko'rish: telefoningizdagi Telegram'da `https://t.me/sifat_edubot?start=sinov` ni oching.
Bosh admin akkauntingiz botga ulangan bo'lsa — menyuda «🎯 Daraja testi»; yangi raqam bilan esa
odamlar ko'radigan to'liq yo'l (ro'yxatdan o'tish → yo'nalish → test → kupon → ariza).
