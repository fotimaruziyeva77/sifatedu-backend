# O'qituvchi kabineti: o'quvchilar, dars jadvali, yo'qlama va imtihon

Saytda: **Kabinet → «Guruhlarim»** → guruhni oching. O'qituvchi faqat o'z guruhlarini ko'radi.

## O'quvchi qo'shish

1. «O'quvchilar» bo'limida **«O'quvchi qo'shish»** tugmasini bosing.
2. Telefon raqami (+998 …), ismi va familiyasini yozing → **«Qo'shish»**.

- O'quvchi tizimda bo'lmasa, akkaunti yaratiladi. Unga bot havolasini yuboring (formada
  «Bot havolasini nusxalash» tugmasi bor): o'quvchi botga **shu raqam** bilan kirib, kontaktini
  yuborsa, akkaunti o'zi ulanadi — yangi akkaunt ochilmaydi.
- O'quvchi kursga qo'lda, muddatsiz yoziladi va unga «kurs ochildi» xabari boradi.
- Boshqa guruhda o'qiyotgan bo'lsa — shu guruhga o'tkaziladi (to'lov muddati o'zgarmaydi).
- Xodim (o'qituvchi, menejer, admin) raqamini o'quvchi qilib qo'shib bo'lmaydi.

## Guruhdan chiqarish

O'quvchi ismi ostidagi **«Guruhdan chiqarish»** → tasdiqlang. Kursga kirishi yopiladi; davomati,
test va imtihon natijalari tarixda qoladi. Qaytsa — yana «O'quvchi qo'shish» bilan qo'shasiz.

## Dars jadvali va yo'qlama

1. **«Dars jadvali»** bo'limida kun, soat va davomiylikni tanlab **«Jadvalga qo'shish»**
   (masalan, Dushanba 18:00, Chorshanba 18:00, Juma 18:00).
2. Darslar 2 hafta oldinga o'zi yaratiladi va har kecha to'ldiriladi. O'quvchilarga dars oldidan
   eslatma boradi.
3. **Yo'qlama:** «Jonli darslar» ro'yxatidan darsni oching → har o'quvchiga Keldi / Kechikdi /
   Kelmadi / Sababli («Qolganlar — keldi» tugmasi hammani birdan belgilaydi) → «Davomatni
   saqlash». Dars boshlanishiga 15 daqiqa qolgandan keyin belgilash mumkin. Kelmaganlarga dars
   tugagach botda xabar boradi, XP avvalgidek hisoblanadi.

Jadvaldan darsni olib tashlasangiz (🗑), kelgusi, hali yo'qlama qilinmagan darslar ham o'chadi.

## Imtihonni belgilangan o'quvchilarga ochish

**Kabinet → «Guruhlarim» → «Oylik imtihonlar»** → imtihonni oching.

1. Jadvalda o'quvchilarni belgilang (yoki «Hammasini tanlash»).
2. «Tanlanganlarga ochish» bo'limida **«Qachongacha»**ni tanlang → **«Ochish»**.

Belgilangan o'quvchilar shu vaqtgacha test ishlaydi (saytda yoki botdagi «📝 Testlar»da) va amaliy
topshiriqlarni yuboradi; ularga kabinet va botga xabar boradi. Test — bitta urinish: avval
boshlagan o'quvchi testni qayta ishlay olmaydi, faqat amaliy topshiriqlarni yuboradi. Qoralama
imtihon ochilmaydi — avval admin panelda «Tayyor» qiling.

Yangi amaliy topshiriqlar bilan qayta imtihon kerak bo'lsa — serverdagi skript:
`backend/scripts/imtihon_python_qayta.py`.
