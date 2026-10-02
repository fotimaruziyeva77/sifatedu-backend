# Serverga ishga tushirish (production)

Sayt `https://sifatedu.uz` da, bot webhook bilan, haqiqiy to'lov va SMS bilan ishlashi uchun
qadam-baqadam qo'llanma. Har bir qadamda: nima qilinadi, qaysi buyruq va qanday natija
kutiladi. Taxminiy vaqt — 1,5–2 soat (ko'pi kutish: yig'ish va DNS).

**Qoidalar:**

- Buyruqlarni o'zgartirmasdan nusxa olib qo'ying. `SERVER_IP` o'rniga serveringiz IP manzilini
  yozing.
- Parol, token va kalitlarni **faqat serverda** yozing. Chatga, xatga yoki skrinshotga
  qo'ymang.
- Biror qadam kutilganidek bo'lmasa, to'xtang va buyruq natijasini dasturchiga yuboring
  (maxfiy qiymat chiqmaydigan holat buyrug'i — 15-qadam).

Arxitektura: bitta VPS'da Docker Compose — PostgreSQL, Redis, SeaweedFS (fayllar va videolar),
backend (Django), Celery (oddiy, AI va video navbatlari), frontend (Next.js), nginx (HTTPS) va
kunlik zaxira. Shaxsiy ma'lumotlar va ularning zaxirasi O'zbekistondagi serverda turadi
(shaxsga doir ma'lumotlar to'g'risidagi qonun talabi).

| Manzil | Nima |
|---|---|
| `https://sifatedu.uz` | Sayt, API (`/api/`), admin (`/admin/`) |
| `https://www.sifatedu.uz` | Asosiy manzilga yo'naltiriladi |
| `https://media.sifatedu.uz` | Fayllar va videolar (brauzer to'g'ridan-to'g'ri, imzolangan havolalar bilan) |

**Ikki rejim:**

- **Alohida server** (tavsiya: AHOST, Toshkent) — server faqat Sifat uchun. Quyidagi 1–15-qadamlar.
- **Umumiy server** — serverda boshqa loyihalar ham bor va 80/443 portlarini serverdagi nginx
  ushlab turibdi. Bunda 6, 8 va 9-qadamlar o'rniga oxiridagi
  [Umumiy server](#umumiy-server-boshqa-loyihalar-bilan) bo'limi bajariladi.

## 0. Oldindan tayyorlab qo'ying

| Nima | Qayerdan |
|---|---|
| VPS va uning IP manzili | 1-qadam |
| Faol domen `sifatedu.uz` | AHOST → Domenlar (holati "faol" bo'lsin) |
| E-pochta (Let's Encrypt sertifikati eslatmalari uchun) | o'zingizniki |
| Telegram bot tokeni | @BotFather → `/mybots` → @sifat_edubot → API Token |
| Arizalar guruhi ID | kompyuterdagi `backend/.env` → `TELEGRAM_LEADS_CHAT_ID` |
| Click: `SERVICE_ID`, `MERCHANT_ID`, `MERCHANT_USER_ID`, `SECRET_KEY`, STIR | Click merchant kabineti |
| Eskiz: e-pochta va parol | my.eskiz.uz |
| Anthropic API kaliti (va hisobda kredit) | platform.claude.com → API keys |
| Google OAuth Client ID | Google Cloud Console → Credentials |
| Ixtiyoriy: Sentry DSN, UptimeRobot akkaunti | sentry.io, uptimerobot.com |

Hammasi tayyor bo'lmasa ham boshlash mumkin: bo'sh qoldirilgan bo'lim (masalan, Click) keyin
to'ldirilguncha o'chiq turadi.

## 1. VPS buyurtma qilish (AHOST)

- **Tarif:** 4 vCPU, 8 GB RAM, kamida 160 GB NVMe disk (videolar 50 soatgacha).
- **Operatsion tizim:** Ubuntu 24.04 LTS.
- **Joylashuv:** Toshkent (O'zbekistondagi o'quvchilarga TAS-IX orqali tez).
- Buyurtmadan keyin panel yoki xatda: **IP manzil** va **root paroli**.
- Panelda "Backup / Snapshot" xizmati bo'lsa — yoqing (butun disk nusxasi, videolar ham).

## 2. DNS yozuvlari

AHOST → Domenlar → `sifatedu.uz` → DNS boshqaruvi. Uchta **A** yozuv qo'shing:

| Turi | Nomi | Qiymati | TTL |
|---|---|---|---|
| A | `@` | `SERVER_IP` | 3600 |
| A | `www` | `SERVER_IP` | 3600 |
| A | `media` | `SERVER_IP` | 3600 |

Tekshiruv (kompyuterda, PowerShell). Uchalasi ham serveringiz IP'sini ko'rsatishi kerak.
Yangilanish 5–30 daqiqa, ba'zan bir necha soat oladi:

```powershell
nslookup sifatedu.uz
nslookup www.sifatedu.uz
nslookup media.sifatedu.uz
```

## 3. SSH kalit (kompyuterda, bir marta)

Serverga parolsiz, kalit bilan kirasiz — parolni taxmin qilib buzishning iloji qolmaydi.
PowerShell:

```powershell
ssh-keygen -t ed25519 -C "sifatedu-server"
```

Hamma savolga Enter bosing. Agar "already exists. Overwrite?" deb so'rasa — `n` deb javob
bering (mavjud kalitingiz ishlatiladi). Kalitni serverga qo'shing (root paroli bir marta
so'raladi):

```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh root@SERVER_IP "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

Tekshiruv: `ssh root@SERVER_IP` parol so'ramasdan kirishi kerak. Birinchi ulanishda "Are you
sure you want to continue connecting?" savoliga `yes` deb javob bering.

Keyingi barcha buyruqlar **serverda** (shu SSH oynasida) bajariladi.

## 4. GitHub'dan o'qish kaliti (deploy key)

Repozitoriylar yopiq, server ularni o'qishi uchun har biriga alohida kalit kerak (faqat
o'qish, yozish huquqisiz):

```bash
ssh-keygen -t ed25519 -N "" -f ~/.ssh/sifatedu_backend -C "server: sifatedu-backend"
ssh-keygen -t ed25519 -N "" -f ~/.ssh/sifatedu_frontend -C "server: sifatedu-frontend"
cat >> ~/.ssh/config <<'EOF'
Host github-backend
    HostName github.com
    User git
    IdentityFile ~/.ssh/sifatedu_backend
    IdentitiesOnly yes
Host github-frontend
    HostName github.com
    User git
    IdentityFile ~/.ssh/sifatedu_frontend
    IdentitiesOnly yes
EOF
cat ~/.ssh/sifatedu_backend.pub
```

Chiqqan qatorni (`ssh-ed25519 AAAA…` bilan boshlanadi) GitHub'ga qo'shing:
`sifatedu-backend` → **Settings → Deploy keys → Add deploy key**. Title: `server`, Key: shu
qator, **"Allow write access" — belgilamang** → Add key. Keyin frontend uchun:

```bash
cat ~/.ssh/sifatedu_frontend.pub
```

Bu qatorni `sifatedu-frontend` → Settings → Deploy keys ga xuddi shunday qo'shing. Tekshiruv:

```bash
ssh -T github-backend
ssh -T github-frontend
```

Kutilgan natija (birinchi marta `yes` deb javob bering): `Hi fotimaruziyeva77/sifatedu-backend!
You've successfully authenticated…` va frontend uchun ham xuddi shunday.

## 5. Kodni yuklab olish

```bash
git clone github-backend:fotimaruziyeva77/sifatedu-backend.git /srv/sifatedu
git clone github-frontend:fotimaruziyeva77/sifatedu-frontend.git /srv/sifatedu/frontend
cd /srv/sifatedu
echo "alias dc='docker compose --project-directory /srv/sifatedu'" >> ~/.bashrc
source ~/.bashrc
```

`dc` — Sifat'ning Docker Compose buyrug'i, istalgan papkadan ishlaydi. Qaysi fayllar
ishlatilishini 7-qadamda yaratiladigan `.env` dagi `COMPOSE_FILE` belgilaydi.

## 6. Serverni tayyorlash (5–10 daqiqa)

```bash
bash infra/deploy/setup-server.sh
```

Skript: tizimni yangilaydi, Toshkent vaqtini qo'yadi, swap (4 GB), Docker, firewall (faqat 22,
80, 443), fail2ban, avtomatik xavfsizlik yangilanishlari va certbot o'rnatadi. 3-qadamdagi
kalit qo'shilgan bo'lsa, **parol bilan kirishni o'chiradi**.

Kutilgan natija: oxirida "Parol bilan kirish o'chirildi…", Docker va Compose versiyalari.

**Muhim:** eski oynani yopmasdan, **yangi** PowerShell oynasida `ssh root@SERVER_IP` bilan
kirib ko'ring. Kirsa — hammasi joyida. Kirmasa — eski oynada natijani dasturchiga yuboring.

## 7. Sozlamalar (.env fayllari)

```bash
bash infra/deploy/make-env.sh sifatedu.uz
```

Skript maxfiy qiymatlarni (Django kaliti, baza paroli, fayl va video kalitlari) o'zi yaratadi
va 0-qadamdagi ma'lumotlarni so'raydi. Parol va tokenlar yozilganda ekranda ko'rinmaydi —
nusxa olib qo'yib, Enter bosing. Bilmaganini bo'sh qoldiring: oxirida nimalar keyin
to'ldirilishi ko'rsatiladi.

Keyin to'ldirish: `nano backend/.env` (saqlash — Ctrl+O, Enter; chiqish — Ctrl+X), so'ng
`bash infra/deploy/deploy.sh`.

## 8. Yig'ish (10–20 daqiqa)

```bash
dc build
```

Kutilgan natija: oxirida xatosiz `Built` qatorlari. Docker Hub sekin bo'lsa, tizim mirror
(`mirror.gcr.io`) orqali yuklaydi. Tarmoq xatosi bilan to'xtasa — buyruqni qayta ishga
tushiring.

## 9. Ishga tushirish va HTTPS

```bash
bash infra/deploy/init-cert.sh sizning@pochtangiz.uz
```

Skript avval DNS'ni tekshiradi (uchala nom shu serverga qaraydimi), so'ng hamma servislarni
ishga tushiradi (birinchi marta baza tayyorlanadi, 2–4 daqiqa), Let's Encrypt sertifikatini
oladi va nginx'ga ulaydi.

Kutilgan natija: `Successfully received certificate`, oxirida:

```
https://sifatedu.uz/ → 200
https://www.sifatedu.uz/ → 301
https://media.sifatedu.uz/ → 403
```

Brauzerda `https://sifatedu.uz` oching — qulf belgisi bilan ochilishi kerak. Sertifikat
avtomatik yangilanadi (certbot kuniga 2 marta tekshiradi).

## 10. Admin akkaunt va kontent

```bash
dc exec backend python manage.py createsuperuser
```

Telefon (`+998…`) va kuchli parolni yozing. Bu parolni serverda yozasiz va hech kimga
yubormaysiz. So'ng `https://sifatedu.uz/admin/` ga kiring va quyidagilarni qiling:

- kurslar, narxlar va ustozlarni kiriting (har kursda **MXIK kodi** — fiskal chek uchun);
- xodimlarga rollarni bering (Menejer, O'qituvchi, Direktor);
- o'yin sozlamalarini va do'kon sovg'alarini kiriting.

Kompyuterdagi local bazadan kurslarni ko'chirish kerak bo'lsa — dasturchiga ayting.

## 11. Telegram bot

Bitta bot tokeni bir vaqtda ham serverda (webhook), ham kompyuterda (polling) ishlay olmaydi.
Shuning uchun bu qadamdan oldin dasturchiga ayting: kompyuterdagi bot to'xtatiladi va local
sinov uchun alohida test bot ulanadi.

```bash
dc exec backend python manage.py telegram_webhook set
dc exec backend python manage.py bot_setup
```

Kutilgan natija: `Webhook o'rnatildi: https://sifatedu.uz/api/v1/bot/webhook/`.

Keyin @BotFather'da `/setdomain` → @sifat_edubot → `sifatedu.uz` kiriting. Bu saytdagi
"Telegram orqali kirish" tugmasi uchun kerak.

Tekshiruv: botda `/start` va menyuni bosib ko'ring. Saytga olib boradigan havolalar endi
xabar ostida tugma bo'lib chiqadi. Admin akkauntingiz Telegram'ga ulangan bo'lsa (kabinet →
Sozlamalar → «Telegram'ni ulash»), menyuda «📊 Admin panel» ham bor.

## 12. To'lov, SMS va Google

**Click** — merchant kabinetida servis sozlamalari:

- Prepare URL: `https://sifatedu.uz/api/v1/payments/click/prepare/`
- Complete URL: `https://sifatedu.uz/api/v1/payments/click/complete/`

Sinov: bitta kursga vaqtincha 1 000 so'm narx qo'yib, o'zingiz sotib oling. To'lov o'tishini,
kurs ochilishini va fiskal chek kelishini tekshiring. So'ng pulni qaytaring (admin →
To'lovlar → Pul qaytarish) va narxni joyiga qo'ying.

**Eskiz** — SMS shablonlari moderatsiyadan o'tgan bo'lsin. Sinov: saytda yangi raqam bilan
ro'yxatdan o'ting — kod SMS bo'lib kelishi kerak.

**Google** — Cloud Console → Credentials → OAuth client → **Authorized JavaScript origins** ga
`https://sifatedu.uz` qo'shing. Sinov: "Google bilan kirish".

## 13. Kuzatuv (monitoring)

- **UptimeRobot** (uptimerobot.com, bepul): ikkita HTTPS monitor — `https://sifatedu.uz/healthz`
  va `https://sifatedu.uz/api/v1/health/`, har 5 daqiqada. Ogohlantirish: Telegram yoki
  e-pochta. Sayt ishlamay qolsa, bir necha daqiqada xabar keladi.
- **Server resurslari** avtomatik tekshiriladi (soatda bir). Disk 85% dan oshsa yoki bo'sh
  xotira 10% dan kam qolsa, texnik guruhga (`TELEGRAM_ALERTS_CHAT_ID`) Telegram xabar keladi
  va admin bosh sahifasidagi "Muammolar"da chiqadi.
- **Sentry** (ixtiyoriy): xatolar tafsiloti bilan. DSN `backend/.env` va root `.env` da.

## 14. Zaxira nusxalar

- **Baza:** har kuni 03:00 da `/srv/sifatedu/backups` ga, 30 kun saqlanadi. Har nusxa yozilgach
  tekshiriladi.
- **Haftada bir marta** kompyuterga ham nusxa oling (server butunlay ishdan chiqsa ham ma'lumot
  qoladi). Kompyuterda, PowerShell:

  ```powershell
  mkdir D:\SifatEdu-zaxira -Force
  scp "root@SERVER_IP:/srv/sifatedu/backups/*" D:\SifatEdu-zaxira\
  ```

- **Videolar** bazaga kirmaydi. Yuklangan videolarning asl fayllarini o'zingizda saqlang;
  AHOST'da snapshot xizmati bo'lsa — yoqing.
- **Tiklash:** `infra/backup/README.md`. Ishga tushgach bir marta sinab ko'rish tavsiya etiladi
  (dasturchi bilan).

## 15. Yangilash va holat

Yangi versiyani chiqarish (dasturchi GitHub'ga yuklagandan keyin):

```bash
bash /srv/sifatedu/infra/deploy/deploy.sh
```

Skript ikkala repozitoriyni yangilaydi, yig'adi, ishga tushiradi va https orqali tekshiradi.
Tekshiruvdan o'tmasa, avtomatik oldingi versiyaga qaytadi va loglarni ko'rish buyrug'ini
yozadi. Odatda 5–15 daqiqa.

Umumiy holat — versiya, konteynerlar, sayt, sertifikat muddati, bot webhook, oxirgi zaxira,
disk va xotira (maxfiy qiymat chiqmaydi, natijani dasturchiga yuborsa bo'ladi):

```bash
bash /srv/sifatedu/infra/deploy/status.sh
```

## Muammo bo'lsa

| Belgi | Nima qilish kerak |
|---|---|
| `init-cert.sh`: "→ topilmadi" yoki boshqa IP | DNS yozuvlarini tekshiring (2-qadam) va 10–30 daqiqa kuting |
| Sertifikat olinmadi | `ufw status` da 80 va 443 ochiq bo'lsin; DNS to'g'ri bo'lsin. Let's Encrypt soatiga 5 ta xatodan keyin vaqtincha to'xtatadi — 1 soat kuting |
| `dc build` tarmoq xatosi bilan to'xtadi | Qayta ishga tushiring; takrorlansa — natijani dasturchiga yuboring |
| Sayt 502 yoki 504 qaytaryapti | `dc ps` (hamma `healthy` bo'lsin), `dc logs --tail=100 backend frontend` |
| Konteyner qayta-qayta o'chib yonyapti | `dc logs --tail=200 <servis nomi>` |
| Disk to'lyapti | `df -h /`, `docker system df`; eski yoki keraksiz videolarni admin'dan o'chiring; AHOST'da diskni kengaytiring |
| Bot javob bermayapti | `dc exec backend python manage.py telegram_webhook info` — `last_error_message` ga qarang |

Foydali buyruqlar:

```bash
dc ps                          # konteynerlar holati
dc logs -f --tail=100 backend  # backend loglari (chiqish — Ctrl+C)
dc restart backend             # bitta servisni qayta ishga tushirish
dc exec backend python manage.py check --deploy   # Django xavfsizlik tekshiruvi
```

## Umumiy server (boshqa loyihalar bilan)

Serverda boshqa saytlar ham ishlayotgan bo'lsa va 80/443 portlarini serverdagi nginx ushlab
turgan bo'lsa, Sifat o'sha nginx'ning orqasida, faqat ichki portda (`127.0.0.1:8090`) ishlaydi.
HTTPS va sertifikat — serverdagi nginx'da (`certbot --nginx`). Boshqa loyihalarga tegilmaydi.

> **Eslatma:** server O'zbekistondan tashqarida bo'lsa, shaxsiy ma'lumotlar qonuni (27¹-modda)
> bo'yicha xavf bor. Keyinchalik O'zbekistondagi serverga ko'chirish tavsiya etiladi — bu shu
> qo'llanmaning alohida server rejimi bilan qilinadi.

**Kerak:** Docker va Compose plugin, nginx, certbot va uning nginx plagini
(`apt install python3-certbot-nginx`). **`setup-server.sh` ishga tushirilmaydi** — u firewall,
SSH va Docker sozlamalarini o'zgartiradi va boshqa loyihalarga ta'sir qiladi.

**Joylashuv:** frontend backend papkasi ichida bo'lishi kerak (`<loyiha>/frontend`).

**Xotira:** Sifat odatda 1,3–1,8 GB oladi (video qayta ishlanganda ko'proq). `free -h` dagi
`available` kamida 2 GB bo'lsin. Bu rejimda har bir Sifat konteynerining xotirasi chegaralangan:
oshib ketsa, faqat o'sha konteyner to'xtaydi, boshqa loyihalarga tegmaydi. Image'lar birma-bir
yig'iladi. Swap bo'lmasa (`swapon --show` bo'sh chiqsa), 4 GB swap qo'shish tavsiya etiladi:

```bash
fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

1. **Bo'sh ichki port:** quyidagi buyruq birinchi bo'sh portni chiqaradi — quyida 8090 o'rniga
   shuni yozing:

   ```bash
   for p in 8090 8095 8096 8097 8098 8099; do ss -ltn | grep -q ":$p " || { echo "bo'sh port: $p"; break; }; done
   ```
2. **Sozlamalar:** `bash infra/deploy/make-env.sh sifatedu.uz umumiy 8090` (7-qadamdagi savollar).
3. **Yig'ish va ishga tushirish** (10–20 daqiqa):

   ```bash
   dc build
   dc up -d
   dc ps
   curl -s -H 'Host: sifatedu.uz' http://127.0.0.1:8090/api/v1/health/
   ```

   Kutilgan natija: `dc ps` da hamma servis `healthy` (birinchi marta 2–4 daqiqa),
   `curl` — `{"status":"ok", ...}`.
4. **Serverdagi nginx:**

   ```bash
   cp infra/deploy/host-nginx.conf /etc/nginx/sites-available/sifatedu
   ln -s /etc/nginx/sites-available/sifatedu /etc/nginx/sites-enabled/sifatedu
   nginx -t && systemctl reload nginx
   ```

   Port 8090 bo'lmasa: `sed -i 's/127.0.0.1:8090/127.0.0.1:PORT/' /etc/nginx/sites-available/sifatedu`.
5. **HTTPS** (DNS serverga qaragandan keyin, 2-qadam):

   ```bash
   certbot --nginx --redirect -d sifatedu.uz -d www.sifatedu.uz -d media.sifatedu.uz
   ```

   Kutilgan natija: `Successfully deployed certificate`. Sertifikat avtomatik yangilanadi.
6. **Tekshiruv:** `bash infra/deploy/status.sh` — sayt 200, ikkala sertifikat muddati ko'rinadi.

Keyin 10-qadamdan davom eting. Yangilash ham shu: `bash infra/deploy/deploy.sh`.
