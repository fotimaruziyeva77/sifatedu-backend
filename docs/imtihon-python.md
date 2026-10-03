# Python guruhi — oylik imtihon: qadam-baqadam

Hamma buyruqlar serverda, `/srv/sifatedu` papkasida. Har safar boshida:

```bash
cd /srv/sifatedu && git pull
S=backend/scripts/imtihon_python_oktabr.py
```

## 1. Sayt va bot ishlayaptimi (bir marta)

```bash
curl -s https://sifatedu.uz/api/v1/health/; echo
dc exec -T backend python manage.py telegram_webhook info | grep -E '"url"|last_error'
```

- `{"status":"ok", ...}` chiqmasa, HTTPS yo'q:
  `certbot --nginx --redirect -d sifatedu.uz -d www.sifatedu.uz`.
- `"url"` bo'sh bo'lsa, bot ulanmagan:

  ```bash
  dc exec -T backend python manage.py telegram_webhook set
  dc exec -T backend python manage.py bot_setup
  ```

## 2. Admin akkaunt (bir marta)

```bash
dc exec backend python manage.py createsuperuser
```

Telefon (`+998…`) va parol. Shu bilan saytga kirib baholaysiz.

## 3. Imtihonni yuklash (bir marta)

```bash
dc exec -T -e ACTION=setup backend python manage.py shell < $S
```

Kutilgan natija: `Savollar banki: 32 ta, imtihonda: 20 ta, 40 daqiqa`, `Amaliy topshiriqlar: 4 ta`.

## 4. O'quvchilar botga qo'shiladi (darsda)

Havola: **https://t.me/sifat_edubot** → **Start** → tilni tanlash → **«📱 Telefonni yuborish»**.
Faqat +998 raqamlar qabul qilinadi. Akkaunt o'zi ochiladi, SMS kerak emas.

## 5. Guruhga qo'shish

```bash
dc exec -T -e ACTION=students backend python manage.py shell < $S
dc exec -T -e ACTION=enroll backend python manage.py shell < $S
```

Birinchisi ro'yxatni ko'rsatadi — o'z ro'yxatingiz bilan solishtiring. Kech qolganlar uchun
4–5-qadamlarni qaytaring: `enroll` faqat yangilarni qo'shadi.

**Begona kishini chiqarish** (guruh va imtihondan; akkaunt qoladi, `enroll` uni qayta qo'shmaydi):

```bash
dc exec -T -e ACTION=remove -e PHONES=+998901234567,+998907654321 backend python manage.py shell < $S
```

## 6. Imtihonni ochish (bir marta)

```bash
dc exec -T -e ACTION=open backend python manage.py shell < $S
```

Standart 3 soat; boshqacha kerak bo'lsa, `-e HOURS=2` qo'shing. Guruhdagilarga botda xabar
boradi. Keyin qo'shilganlar imtihonni botdagi «📝 Testlar» bo'limidan topadi.

## 7. O'quvchi nima qiladi

- **Test** — botda: **«📝 Testlar» → oylik imtihon → «▶️ Boshlash»**. 20 savol, 40 daqiqa,
  bitta urinish.
- **Amaliy** — saytda: botdagi imtihon xabaridagi **«🖥 Amaliy topshiriqlar»** tugmasi saytni
  parolsiz ochadi. Har bir topshiriqqa kodni qo'yib **«Yuborish»** bosiladi. Kompyuterda bajarish
  uchun Telegram'ni shu kompyuterda ochib (Telegram Desktop yoki web.telegram.org) tugmani
  bosishadi. Havola 10 daqiqa amal qiladi — muddati o'tsa, tugmani yana bosishadi.

## 8. Kuzatish

```bash
dc exec -T -e ACTION=status backend python manage.py shell < $S
```

Har bir o'quvchi bo'yicha: test (boshlamagan / ishlayapti / foiz) va amaliy (nechta yuborgan).

## 9. Yopish (hamma tugatganda yoki muddat tugaganda o'zi yopiladi)

```bash
dc exec -T -e ACTION=close backend python manage.py shell < $S
```

Javob qabul qilish to'xtaydi, tugatilmagan testlar yakunlanadi, o'quvchilar to'g'ri javoblarni
ko'radi.

## 10. Baholash

**https://sifatedu.uz** ga admin telefon va parolingiz bilan kiring → kabinet → **«O'qitish»** →
imtihon. Har bir topshiriqqa 0–100 ball qo'yiladi. O'quvchining 4 ta topshirig'i baholanishi bilan
unga yakuniy natija o'zi boradi: test 50% + amaliy 50%, o'tish bali 60%.

## Muammo bo'lsa

| Belgi | Nima qilish kerak |
|---|---|
| Bot javob bermayapti | `dc exec -T backend python manage.py telegram_webhook info` — `last_error_message`; `dc logs --tail=50 backend` |
| O'quvchi `students` ro'yxatida yo'q | U «📱 Telefonni yuborish» tugmasini bosmagan |
| O'quvchi botda imtihonni ko'rmayapti | `enroll` qilinmagan yoki imtihon ochilmagan (`status`) |
| «Amaliy topshiriqlar» kirish sahifasini ochdi | Havola eskirgan — botda tugmani yana bosish kerak |
| Vaqt yetmayapti | `open` ni `-e HOURS=…` bilan qayta ishga tushiring (boshlangan testlar o'z vaqtini saqlaydi) |
| Kelmagan o'quvchiga keyin topshirish kerak | Kabinetdagi imtihon sahifasida unga «alohida muddat» bering |

## 11. Natijalar (terminalda va Excel'da)

```bash
dc exec -T -e ACTION=results backend python manage.py shell < $S
dc exec -T -e ACTION=excel backend python manage.py shell < $S
dc cp backend:/tmp/python-natijalar.xlsx /srv/sifatedu/python-natijalar.xlsx
```

Excel'da o'tganlar yashil, o'tmaganlar qizil, baholash tugamaganlar sariq. Faylni kompyuterga
olish (PowerShell):

```powershell
scp root@100.42.190.208:/srv/sifatedu/python-natijalar.xlsx $env:USERPROFILE\Desktop\
```
