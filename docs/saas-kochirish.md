# Sifat Edu'ni ko'p markazli tuzilishga o'tkazish

Bir marta bajariladi. Hozirgi hamma jadval `public` sxemadan `sifat` sxemaga o'tadi: ma'lumot
qayta yozilmaydi, ID'lar va fayllar o'zgarmaydi. `public`da faqat platforma qoladi: markazlar,
manzillar, super admin. Buyruqlarni serverda siz ishga tushirasiz, hammasi
[`infra/deploy/adopt.sh`](../infra/deploy/adopt.sh) ichida.

## 1. Sinov (saytga tegmaydi)

Yangi kod alohida papkaga olinadi, jonli baza nusxasida ko'chirish bajariladi va vaqti o'lchanadi.
Ma'lumot serverdan chiqmaydi, nusxa oxirida o'chiriladi.

```bash
cd /srv/sifatedu
git fetch origin saas/23-asos
git worktree add /srv/sifatedu-sinov FETCH_HEAD
bash /srv/sifatedu-sinov/infra/deploy/adopt.sh rehearse
git worktree remove /srv/sifatedu-sinov
```

Oxirgi qatorlarda `Sinov muvaffaqiyatli` chiqishi kerak. Natijani yuboring: ko'chirish vaqti shu
yerdan ma'lum bo'ladi.

## 2. Ko'chirish

Kechasi, darslar yo'q paytda. Sayt va bot taxminan 5–10 daqiqa ishlamaydi (aniq vaqt sinovdan
ma'lum bo'ladi); Telegram botga kelgan xabarlarni keyin qayta yuboradi.

Men kodni `main`ga qo'shganimdan keyin:

```bash
cd /srv/sifatedu
git pull --ff-only
git -C frontend pull --ff-only
bash infra/deploy/adopt.sh move
```

Bu buyruqlar orasida `deploy.sh` ishga tushirilmaydi. Tasodifan ishga tushsa ham baza buzilmaydi:
yangi backend eski bazani ko'rib to'xtaydi (`adopt_center --check`).

Skript tartibi: image'lar yig'iladi (sayt hali ishlayapti) → sayt va jadval to'xtaydi → bajarilayotgan
vazifalar kutiladi → to'liq zaxira → ko'chirish (bitta tranzaksiya: xato bo'lsa baza o'zgarmaydi) →
ishga tushirish → tekshiruv.

Navbat 5 daqiqada bo'shamasa, skript saytni qayta yoqib to'xtaydi — hech narsa o'zgarmagan bo'ladi.

## 3. Tekshiruv

Skript o'zi tekshiradi: sayt, API, kurslar ro'yxati va hamma jadval o'qilishi. Keyin qo'lda:

- saytga kirish va o'quvchi kabineti, dars ochish;
- admin panelga kirish;
- botga `/start`;
- `bash infra/deploy/status.sh`.

## 4. Muammo chiqsa

`move` oxirida zaxira fayli nomi chiqadi. Faqat ko'chirishdan keyin darhol ishlating: keyingi
yangi yozuvlar yo'qoladi.

```bash
bash /srv/sifatedu/infra/deploy/adopt.sh rollback /backups/<fayl>.dump
```

Baza zaxiradan tiklanadi va oldingi image'lar ishga tushadi. Tuzatilgunicha `deploy.sh`
ishga tushirilmaydi.

## 5. Ko'chirishdan keyin buyruqlar

`manage.py` endi sukut bo'yicha platformada (`public`) ishlaydi. Markaz ma'lumotlari bilan
ishlaydigan buyruq `tenant_command` orqali beriladi:

```bash
dc exec backend python manage.py tenant_command telegram_webhook --schema=sifat info
dc exec -T backend python manage.py tenant_command shell --schema=sifat < skript.py
```

Noto'g'ri berilsa, buyruq «jadval yo'q» xatosi bilan to'xtaydi — ma'lumotga zarar yetmaydi.
`deploy.sh` o'zgarmaydi: migratsiyalar hamma markazga avtomatik o'tadi.

## 6. Super admin paneli

Ko'chirish uchun shart emas, panel kerak bo'lganda:

1. DNS: `platform.sifatedu.uz` — A yozuv, server IP'si.
2. `/etc/nginx/sites-available/sifatedu`dagi `server_name` qatorlariga `platform.sifatedu.uz`ni
   qo'shing, keyin:

   ```bash
   nginx -t && systemctl reload nginx
   certbot --nginx --redirect --expand -d sifatedu.uz -d www.sifatedu.uz -d media.sifatedu.uz -d platform.sifatedu.uz
   ```

3. Platforma admini (parolni o'zingiz terasiz, u markaz adminlaridan alohida):

   ```bash
   dc exec backend python manage.py createsuperuser
   ```

4. Panel: `https://platform.sifatedu.uz/admin/`.
