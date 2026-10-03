# AI maslahatchi (Google Gemini): ulash va birga «o'qitish»

AI maslahatchi saytdagi chatda va Telegram botda («💬 Savol berish» yoki istalgan erkin matn)
kechayu kunduz javob beradi. U samimiy, xuddi odamdek gaplashadi va halol ishontiradi. Mos kursni
tavsiya qiladi, keyin bepul daraja testiga yoki bepul maslahatga olib boradi: raqamni olib,
menejerlarga ariza qoldiradi. AI **faqat siz kiritgan faktlarni** aytadi. Narx, chegirma yoki ishga
joylashtirishni o'zidan to'qimaydi: bilmagan narsasini «menejerimiz aniq aytadi» deb, raqam so'raydi.

Model — **Gemini 3.8 Flash** (barqaror, tez). Uni `.env` dagi `GEMINI_MODEL` bilan almashtirsa
bo'ladi. Gemini ishlamay qolsa yoki budjet tugasa, oddiy rejim yoqiladi: kurslarni ko'rsatadi va
raqam so'raydi. Mijoz javobsiz qolmaydi.

## 1. Kalit (bir marta, ~10 daqiqa)

1. [aistudio.google.com](https://aistudio.google.com) → Google akkauntingiz bilan kiring →
   **Get API key** → **Create API key**.
2. **Billing** (pullik tarif) — AI Studio'da loyiha yonidagi **Set up billing** (karta orqali).
   Bu muhim: bepul tarifda yozishmalar Google mahsulotlarini yaxshilashga ishlatilishi mumkin va
   limitlari juda kichik. Gemini ilovasidagi **Pro obuna API bermaydi** — bu alohida narsa.
3. Kalitni **chatga yubormang** — uni faqat serverda kiritasiz:

   ```bash
   read -rsp "Gemini kaliti: " K && echo "GEMINI_API_KEY=$K" >> /srv/sifatedu/backend/.env && unset K && echo
   ```
   ```bash
   bash /srv/sifatedu/infra/deploy/deploy.sh
   ```

4. Admin → **AI yordamchi → AI sozlamalari**: kunlik va oylik budjet ($). Bitta javob taxminan
   $0,005–0,01 turadi, 10 xabarli suhbat — $0,05–0,1. Oylik budjetning 80 foiziga yetganda
   Telegram'ga ogohlantirish keladi.

Narx (1M token, kiruvchi / chiquvchi): $1,50 / $7,50. 2026 yil oxirigacha aksiya bor — $0,75 /
$3,75. Budjet zaxira bilan, aksiyasiz narxda hisoblanadi.

## 2. AI nimani biladi va uni qayerda o'zgartirasiz

| Nima | Admin'da qayerda |
|---|---|
| Kurslar: narx, dastur, ustozlar, davomiylik, sertifikat | **Kurslar** (faqat «Nashr qilingan»lari) |
| Telefon, manzil, ish vaqti, Telegram, Instagram | **Sayt kontenti → Sozlamalar va hero** |
| Ko'p beriladigan savollar | **Sayt kontenti → FAQ** |
| Landing'dagi «Sizga ham tanishmi?» xavotirlari | **Sayt kontenti → Xavotirlar** |
| Boshqa hamma faktlar va **e'tirozlarga javoblar** | **AI yordamchi → AI sozlamalari → Qo'shimcha ma'lumot** |
| Bepul daraja testi va kupon | o'zi oladi: **Sotuv → Daraja testlari**, **XP va coin → Sozlamalar** |

O'zgartirsangiz, AI keyingi xabardanoq yangi faktni aytadi — qayta ishga tushirish shart emas.

## 3. Savolnoma — birga to'ldiramiz

Javoblarni menga yozing (yoki o'zingiz «Qo'shimcha ma'lumot»ga kiriting). Qancha aniq bo'lsa, AI
shuncha yaxshi ishontiradi:

1. Har kurs uchun narx: onlayn (bir marta) va offlayn (oyiga). Hozirgi aksiyalar bormi?
2. Bo'lib to'lash mumkinmi? Qanday shartlarda?
3. Offlayn guruhlar: qaysi kunlari, soat nechada, bitta guruhda necha kishi?
4. Dars davomiyligi va kurs davomiyligi (necha oy).
5. Manzil va mo'ljal (qayerga yaqin), avtobus yoki metro.
6. Bepul sinov darsi yoki ochiq dars bormi? Qachon?
7. Ustozlar: tajribasi, qayerda ishlagan — faqat aytishga rozi bo'lgan narsalar.
8. Kurs oxirida nima qila oladi (portfolio, loyihalar)? Bitiruvchilarning real natijalari.
9. Ishga joylashishga yordam berasizmi? **Va'da bermaysiz** — qanday yordam aniq bor?
10. Noutbuk kerakmi? Darsga o'z kompyuteri bilan keladimi?
11. Yosh chegarasi: eng kichik va kattalar uchun.
12. To'lov qaytariladimi (qanday holatda)?
13. Boshqa markazlardan nimangiz bilan farq qilasiz (3 ta asosiy sabab)?
14. Ota-onalar uchun (SIFAT Kids): farzandi qanday o'qishini qayerda ko'radi?
15. Menejerlar ish vaqti va qo'ng'iroq qilish odati (masalan, «1 soat ichida»).

## 4. E'tirozlarga javoblar — qoralama

Ularni o'qib chiqing, `[...]` joylarini to'ldiring va keragini **Qo'shimcha ma'lumot**ga shu
ko'rinishda qo'ying: `E'tiroz: … → Javob: …`. AI javobni o'z so'zlari bilan, suhbatga moslab
aytadi.

| E'tiroz | Halol javob (qoralama) |
|---|---|
| «Qimmat» | Narx kursning to'liq dasturi, ustoz va amaliyot uchun. Onlayn varianti arzonroq — [narx]. Bepul daraja testidan keyin 15–25% chegirma kuponi olsa bo'ladi. [Bo'lib to'lash: …] |
| «Vaqtim yo'q» | Haftasiga [N] soat yetarli. Onlayn kursni o'zingizga qulay vaqtda o'qiysiz, offlayn guruhlar [kunlar/soatlar]. |
| «Uddalay olmayman», «matematikam yomon» | Kurs noldan boshlanadi; [N]% o'quvchimiz ham dasturlashni bilmay kelgan. Daraja testi qayerdan boshlashni ko'rsatadi. |
| «O'ylab ko'raman» | Albatta, shoshilmang. Nima o'ylantiryapti — narxmi, vaqtmi? Bepul daraja testini ishlab ko'ring: majburiyat yo'q, kupon 72 soat turadi. |
| «Onlayn o'qish samarasiz» | Botda har dars testi, uy vazifasini ustoz tekshiradi, oylik imtihon bor — o'quvchi o'qiyotganini o'zi ham, ota-onasi ham ko'radi. [Offlayn varianti ham bor.] |
| «Ish topa olamanmi?» | Kafolat bermaymiz — halol aytamiz. Kurs oxirida [portfolio/loyihalar] bo'ladi, [qanday yordam: rezyume, tavsiya …]. |
| «Kompyuterim yo'q» | [Markazda kompyuter bormi? Yoki noutbuk talabi.] |
| «Yoshim katta» | [Yuqori yosh chegarasi yo'q]; kattalar ham noldan o'rganib, ishga kirgan. [Misol bo'lsa.] |
| «Boshqa joyda arzonroq» | Boshqa markazlarni yomonlamaymiz. Bizda [3 ta farq: masalan, botda testlar va eslatmalar, sertifikat QR bilan, kichik guruh]. |

## 5. Sinash va yaxshilash

- **Avtomatik sinov** (haqiqiy Gemini, 3 tilda, ~$0,05–0,2):
  `dc exec backend python manage.py assistant_eval --show`.
- **Haqiqiy suhbatlar**: admin → **AI yordamchi → Suhbatlar**. U yerda 👎 baholar filtri va
  «Menejer kerak» holati bor. Haftada bir 10 ta suhbatni o'qing. AI noto'g'ri yoki ishonchsiz javob
  bergan bo'lsa, kerakli faktni FAQ'ga yoki «Qo'shimcha ma'lumot»ga qo'shing. Ko'p hollarda AI'ga
  shu yetishmagan bo'ladi.
- Ohang (samimiylik, ishontirish) kodda — `backend/apps/assistant/prompt.py` (`RULES`). Uni
  o'zgartirish kerak bo'lsa, menga misol bilan yozing: «shu savolga shunday javob berdi, bunday
  bo'lishi kerak edi».
