# Ko'p markazli CRM (SaaS): reja

2026-11-08 · buyurtmachi so'rovi · **«boshla» deyilgach ish boshlanadi**

Maqsad: istalgan o'quv markazi saytga kirib o'z markazini ochadi va tarifiga kirgan bo'limlarni
ko'radi. Platforma egasi bitta super admin panelidan hamma markazlarni boshqaradi. Sifat Edu —
birinchi markaz: manzili, o'quvchilari va ma'lumotlari o'zgarmaydi.

## 1. Natijada nima bo'ladi

| Kim | Qayerda | Nima qiladi |
|---|---|---|
| Platforma egasi (super admin) | `platforma-domeni/admin/` | Markazlar, tariflar, obuna muddati, to'xtatish, foydalanish hisoboti |
| Markaz egasi va xodimlari | `markaz.platforma-domeni` | O'z markazi: o'quvchilar, guruhlar, to'lovlar, sozlamalar |
| O'quvchi | O'sha manzil va markazning boti | O'qish, test, to'lov |

Markazlar bir-birining ma'lumotini ko'rmaydi. Bir odam ikki markazda o'qisa, ikkita alohida
akkaunt bo'ladi.

## 2. Tariflar

Tarif ikki narsani belgilaydi: qaysi bo'limlar ochiq va cheklovlar. Tariflar kodda emas, super
admin panelida turadi: nom, narx, bo'lim va cheklovlar kod yozmasdan o'zgaradi. Bitta markazga
alohida bo'lim ochib berish ham mumkin.

Boshlang'ich taklif (son va narxlarni siz tasdiqlaysiz):

| Bo'lim | Start | Standart | Pro |
|---|:-:|:-:|:-:|
| O'quvchilar, guruhlar, jadval, davomat, xodimlar | ✓ | ✓ | ✓ |
| Naqd va karta to'lovlar, qarzdorlar | ✓ | ✓ | ✓ |
| Arizalar | ✓ | ✓ | ✓ |
| Sayt: bosh sahifa va kurslar katalogi, nom, logo, rang | ✓ | ✓ | ✓ |
| Lidlar voronkasi va eslatmalar | — | ✓ | ✓ |
| Telegram bot, xabarnomalar, SMS | — | ✓ | ✓ |
| Click orqali online to'lov | — | ✓ | ✓ |
| Xonalar bandligi | — | ✓ | ✓ |
| Dars testlari, uy vazifasi, slaydlar | — | ✓ | ✓ |
| Kunlik test, oylik imtihon, sertifikat | — | — | ✓ |
| Daraja testi va kuponlar | — | — | ✓ |
| XP, reyting, do'kon | — | — | ✓ |
| AI maslahatchi va AI test | — | — | ✓ |
| Video darslar | — | — | ✓ |
| O'z domeni | — | — | ✓ |
| **Filiallar** | 1 | 3 | cheksiz |
| **O'quvchilar** | 100 | 500 | 2 000 |
| **Xodimlar** | 5 | 20 | cheksiz |
| **Disk** | 1 GB | 10 GB | 100 GB |

**Tarifga kirmagan bo'lim hamma joyda yopiq:** sayt menyusi va sahifalari, admin panel menyusi,
API (403), bot menyusi va fon vazifalari. Bog'liq mantiq ham o'chadi: masalan, test bo'limi
bo'lmasa, keyingi dars testga bog'lanmaydi; XP bo'lmasa, ball yozilmaydi.

**Cheklovga yetganda:** mavjud ma'lumot ishlashda davom etadi, yangisi qo'shilmaydi va markaz
egasiga tarifni oshirish taklif qilinadi.

## 3. Markaz qanday ochiladi

1. Platforma saytida tariflar va «Markazni ochish» tugmasi.
2. Forma: markaz nomi, manzil (`najot` → `najot.platforma-domeni`, band va taqiqlangan nomlar
   tekshiriladi), egasining ismi, telefon, parol.
3. Telefon SMS kod bilan tasdiqlanadi.
4. Markaz fonda tayyorlanadi, egasi «tayyorlanmoqda» ekranini ko'radi.
5. Egasi o'z manziliga kiradi va qadamma-qadam sozlaydi: nom, logo, rang → kurs va guruh → tarifga
   qarab bot tokeni, Click va Eskiz kalitlari (keyinroq ham kiritsa bo'ladi).
6. 14 kun bepul sinov. Muddat tugashiga yaqin ogohlantirish, tugagach 7 kun muhlat, keyin
   «To'lov kerak» sahifasi. Ma'lumotlar o'chmaydi. Bu raqamlar super admin panelida o'zgaradi.

## 4. Super admin

- Hamma markazlar: holat, tarif, muddat, o'quvchi soni, disk, AI va SMS sarfi.
- Tarifni o'zgartirish, sinovni uzaytirish, markazni to'xtatish va qayta yoqish.
- Obuna to'lovini qayd qilish: to'lov kiritiladi, muddat uzayadi.
- Tariflarni tahrirlash.
- Akkaunt serverda buyruq bilan yaratiladi, parolni faqat siz kiritasiz.
- Markaz ichidagi ma'lumotlarga (o'quvchilar, to'lovlar) kirmaydi, faqat umumiy sonlarni ko'radi.

## 5. CRM: yangi bo'limlar

Har uchchalasi markaz xodimlari uchun saytdagi kabinetda bo'ladi va tarifga bo'linadi.

| Bo'lim | Nima bo'ladi |
|---|---|
| **Filiallar va xonalar** | Filial: nom, manzil, telefon. Guruh, xona, ariza va to'lov filialga bog'lanadi. Menejer faqat o'z filialini ko'radi, direktor va admin — hammasini. Hisobotlar filial bo'yicha. Xona band bo'lsa, jadvalda ogohlantiradi. Sifat Edu'da bitta «Asosiy» filial avtomatik ochiladi |
| **To'lov va qarzdorlar** | Guruh narxi va chegirma bo'yicha oylik hisob, naqd, karta va o'tkazma to'lovini kiritish, Click to'lovi avtomatik yoziladi, chek raqami, kim qancha qarzdor, botda yoki SMS'da eslatma, kassir bo'yicha kunlik hisobot. To'lov o'chirilmaydi, sababi yozilib bekor qilinadi. To'lov o'quvchining kirish muddatini ham uzaytiradi |
| **Lidlar voronkasi** | Bosqichlar markaz o'zi sozlaydi (Yangi → Bog'lanildi → Sinov darsi → O'quvchi / Yo'qotildi va sabab). Kanban taxta, menejerga biriktirish, qayta qo'ng'iroq sanasi va eslatma, qo'ng'iroq va izohlar tarixi, bir bosishda o'quvchi qilish, manba bo'yicha konversiya |

O'qituvchi maoshi va xarajatlar — tanlanmadi, rejaga kirmaydi.

## 6. Texnik yechim

**Arxitektura o'zgarmaydi (PLAN §7C):** har markaz PostgreSQL'da alohida sxemada,
[`django-tenants`](https://github.com/django-tenants/django-tenants/releases) 4.0.1 yoki yangisi
(Django 5.2 ni qo'llaydi; 4.0.0 gacha sxema nomida SQL injection bo'lgan). 67 modeldagi so'rovlar
deyarli o'zgarmaydi va bitta unutilgan filtr boshqa markaz ma'lumotini ocholmaydi.

| Joy | Hozir | Bo'ladi |
|---|---|---|
| Baza | Bitta sxema | `public`: markaz, domen, tarif, obuna, super admin. Markaz sxemasi: qolgan hammasi |
| Markazni aniqlash | SSR backend'ga manzilni yubormaydi | `X-Forwarded-Host` yuboradi (tashqi qiymatni nginx almashtiradi), markaz domen bo'yicha topiladi |
| Fon vazifalari | 38 ta vazifa, 20 ta jadval; markaz tushunchasi yo'q | Vazifa markaz nomini olib yuradi (`tenant-schemas-celery`); 19 ta jadval har markaz uchun, yopiq bo'lim va to'xtatilgan markaz o'tkaziladi |
| Kesh va sessiya | Umumiy kalitlar | Kalitlar markaz bo'yicha (aks holda bir xil ID'lar to'qnashadi) |
| Fayllar | Prefikssiz | Yangi markazlar `centers/<markaz>/` ichida; Sifat fayllari joyida qoladi |
| Telegram bot | Bitta token | Har markazning tokeni, webhook o'z manzilida |
| Click, Eskiz | `.env` | Markaz sozlamalarida, shifrlangan |
| AI | Bitta kalit | Platforma kaliti, tarif bo'yicha oylik budjet |
| Brend | «Sifat» matnda qattiq yozilgan (backend ~30 qator, frontend ~20 joy) | Nom, logo, rang markaz sozlamasidan |
| Frontend manzili | `NEXT_PUBLIC_APP_URL` build paytida | Har so'rovda domen bo'yicha |
| Tarif tekshiruvi | Yo'q | Bo'limlar ro'yxati; API uchun bitta middleware, admin uchun `User.has_perm`, sayt menyusi uchun `/me` dagi `features` |
| Deploy | Migratsiya backend ishga tushishida | Alohida qadam (`migrate_schemas`, parallel): markazlar ko'paysa ham health-check vaqtidan oshmaydi |
| Zaxira | `pg_dump` butun baza | O'zgarmaydi; bitta markazni tiklash `--schema` bilan; `max_locks_per_transaction` oshiriladi |

**Birinchi ish — ikki sinov:**
- Ulanishlar puli (psycopg pool) va ASGI bilan ikki markazga parallel so'rovlar: ma'lumot
  aralashmasligi kerak. Hujjatlarda bu holat yozilmagan. Muammo chiqsa, pul o'chiriladi.
- Yangi markaz ochilish vaqti o'lchanadi (58 ta migratsiya). Uzoq bo'lsa, tayyor sxemadan nusxa
  olinadi.

**Markazlar aralashmasligi** har bir o'zgarishda avtomatik tekshiriladi: API, kesh, fayl va fon
vazifa. Hozirgi hamma testlar markaz sxemasi ichida ishlaydi.

## 7. Sifat Edu'ni ko'chirish

Eng xavfli qism — jonli baza. Tartib:

1. **Sinov:** serverda vaqtinchalik bazaga oxirgi zaxira tiklanadi, ko'chirish shu nusxada
   bajariladi va vaqti o'lchanadi. Ma'lumot serverdan chiqmaydi.
2. Kelishilgan kechada sayt va bot to'xtatiladi (taxminan 30 daqiqa, aniq vaqt sinovdan ma'lum
   bo'ladi). To'liq zaxira olinadi.
3. Jadvallar `sifat` sxemasiga o'tkaziladi (`ALTER TABLE … SET SCHEMA`): ma'lumot qayta yozilmaydi,
   ID'lar o'zgarmaydi.
4. Markaz, domenlar va `Pro` tarif yoziladi; bot, Click va Eskiz sozlamalari `.env` dan markaz
   sozlamalariga o'tadi. Fayllar va webhook manzillari o'zgarmaydi.
5. Tekshiruv: kirish, dars, test, to'lov, bot.
6. Muammo bo'lsa: oldingi image va zaxiradan qaytariladi.

Serverdagi buyruqlarni siz ishga tushirasiz, men har qadamni tayyor beraman.

## 8. Bosqichlar

| Qadam | Ish | Natijada nima ko'rasiz | Hajmi |
|---|---|---|---|
| **23** | **Asos:** sxemalar, domen bo'yicha aniqlash, fon vazifa, kesh, fayl, aralashmaslik testlari, Sifat Edu ko'chiriladi, super admin | Sifat Edu avvalgidek ishlaydi, super admin paneli ochiladi | katta |
| **24** | **Tarif va bo'limlar:** tariflar, bo'lim yopish, cheklovlar, obuna muddati | Super admin tarifni almashtirsa, sinov markazida bo'limlar yo'qoladi | o'rta |
| **25** | **Markaz o'zi ochiladi:** platforma sayti, ro'yxatdan o'tish, sinov muddati, sozlash ustasi, nom/logo/rang, o'z boti, Click va Eskiz, subdomen va HTTPS | Yangi markaz 5 daqiqada o'zi ochiladi | katta |
| **26** | **CRM:** filiallar va xonalar → to'lov va qarzdorlar → lidlar voronkasi | Sifat Edu'da ham ishlatiladi | katta |
| **27** | **Sotuvga chiqish:** o'z domeni, obuna hisobi, foydalanish hisoboti, oferta, O'zbekistondagi server, markazlar uchun qo'llanma | Birinchi pullik markaz | o'rta |

SIFAT Kids — shulardan keyin. Sifat Edu CRM'dan tezroq foydalansin desangiz, 26-qadamni 24 dan
keyin qilsa bo'ladi.

## 9. Sizdan kerak

| Nima | Qachongacha |
|---|---|
| Tarif son va narxlarini tasdiqlash | 24-qadam |
| Platforma nomi va domeni. Raqobatchi markaz `markaz.sifatedu.uz` manzilini xohlamaydi, shuning uchun alohida neytral domen tavsiya etiladi | 25-qadam |
| Domen DNS'i API'li xizmatda (masalan, Cloudflare): `*.domen` uchun avtomatik HTTPS shart | 25-qadam |
| Eskiz akkaunti: ro'yxatdan o'tishdagi SMS kod uchun | 25-qadam |
| O'zbekistondagi alohida server (4 vCPU, 8 GB, 160 GB). Sabab: shaxsiy ma'lumotlar qonuni 27¹-modda (`DEPLOY.md`) va hozirgi umumiy serverda joy cheklangan | Birinchi pullik markazdan oldin |
| Oferta va markaz bilan shartnoma (yurist). Platforma ma'lumotni markaz nomidan qayta ishlaydi | 27-qadam |

## 10. Qilinmaydi

| Nima | Sabab |
|---|---|
| Super adminning markaz ichiga kirishi (TZ 4.22 dan olib tashlandi) | Xavfli va birinchi versiyaga shart emas; yordam kerak bo'lsa — keyin, markaz ruxsati va jurnal bilan |
| Obunani avtomatik Click orqali olish | Boshida to'lov qo'lda qayd etiladi; markazlar ko'paygach qo'shiladi |
| To'liq dizayn tahriri | Nom, logo va bitta asosiy rang yetadi |
| Bir akkaunt bilan hamma markazlarga kirish | Markazlar mustaqil, §7C qarori |
| Maosh va xarajatlar | Tanlanmadi |

Keyinroq, kelishilsa: tayyor dars dasturlarini (Python va boshqalar) Pro tarifga qo'shish.

## 11. Xavflar

| Xavf | Chora |
|---|---|
| Sifat Edu'ni ko'chirishda nosozlik | Nusxada sinov, zaxira, kechasi, qaytarish yo'li |
| Markaz ma'lumoti aralashishi | Sxema darajasida ajratish, avtomatik testlar, ulanish puli sinovi |
| Ko'p markazda migratsiya va zaxira sekinlashishi | Alohida migratsiya qadami, parallel ishlash, Postgres sozlamasi |
| Mijoz domenida HSTS `includeSubDomains` uning boshqa subdomenlarini ham majburlaydi | Mijoz domenlarida bu parametr olib tashlanadi |
| Hozirgi umumiy serverda joy yetmasligi | Sotuvdan oldin alohida server |
