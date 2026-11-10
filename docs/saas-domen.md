# Platforma domeni va markazlar manzili

Yangi markaz o'zini ochishi uchun platforma nomi va domeni, `*.domen` uchun HTTPS va SMS kerak.
Buyruqlarni serverda siz ishga tushirasiz. Quyida `example.uz` o'rniga o'z domeningizni yozing.

Bular tayyor bo'lguncha oddiy `deploy.sh` xavfsiz: platforma sayti va ro'yxatdan o'tish yopiq
turadi (`SIGNUP_OPEN`), Sifat Edu avvalgidek ishlaydi.

## Nima kerak

| Nima | Nimaga |
|---|---|
| Platforma nomi | Saytda, SMS matnida va super admin panelida ko'rinadi |
| Domen | Platforma sayti `example.uz`, markazlar `nom.example.uz` |
| API'si bor DNS xizmati (masalan, Cloudflare) | `*.example.uz` sertifikati faqat DNS orqali olinadi va o'zi yangilanadi |
| Eskiz akkaunti | Markaz ochishdagi SMS kod va Eskiz'i ulanmagan markazlar o'quvchilarining kirish kodi |

## 1. Birinchi deploy

```bash
bash /srv/sifatedu/infra/deploy/deploy.sh
```

Shu paytda Sifat Edu'ning bot, Click va Eskiz sozlamalari `backend/.env`dan bazaga avtomatik
ko'chadi (shifrlangan holda). Sayt va bot avvalgidek ishlaydi. Keyin ularni kabinetdagi «Markaz
sozlamalari»da o'zgartirasiz. `backend/.env`da `TELEGRAM_BOT_TOKEN` va `TELEGRAM_ALERTS_CHAT_ID`
server ogohlantirishlari uchun qoladi: ularni o'chirmang.

Kalitlar `DJANGO_SECRET_KEY` bilan shifrlanadi. Uni keyinchalik almashtirish kerak bo'lib qolsa,
kalitlar ochilmay qolmasligi uchun alohida sir qo'shib qo'ygan ma'qul (istalgan payt, bir marta):

```bash
cd /srv/sifatedu && grep -q '^INTEGRATIONS_SECRET=' backend/.env || echo "INTEGRATIONS_SECRET=$(openssl rand -hex 32)" >> backend/.env
```

## 2. DNS

Domenni Cloudflare'ga ulang va ikkita A yozuv qo'shing (proksi o'chiq, kulrang bulut):

| Nom | Qiymat |
|---|---|
| `@` | server IP |
| `*` | server IP |

## 3. Wildcard sertifikat

Cloudflare'da API token yarating: My Profile → API Tokens → «Edit zone DNS», faqat shu domen uchun.
Tokenni chatga yozmang, faqat serverda kiriting (ekranda ko'rinmaydi):

```bash
apt install -y python3-certbot-dns-cloudflare
```

```bash
mkdir -p /root/.secrets && read -rsp "Cloudflare token: " T && printf 'dns_cloudflare_api_token = %s\n' "$T" > /root/.secrets/cloudflare.ini && chmod 600 /root/.secrets/cloudflare.ini; echo
```

```bash
certbot certonly --dns-cloudflare --dns-cloudflare-credentials /root/.secrets/cloudflare.ini -d example.uz -d '*.example.uz'
```

Sertifikat o'zi yangilanadi. Boshqa loyihalarning sozlamalariga tegmaydi.

## 4. Nginx

```bash
cd /srv/sifatedu && sed 's/example\.uz/SIZNING-DOMEN/g' infra/deploy/host-nginx-platform.conf > /etc/nginx/sites-available/sifatedu-platform
```

```bash
ln -s /etc/nginx/sites-available/sifatedu-platform /etc/nginx/sites-enabled/sifatedu-platform && nginx -t && systemctl reload nginx
```

## 5. SMS

Eskiz kabinetida shu shablonni tasdiqlatib oling. Boshidagi nom `PLATFORM_NAME` bilan aynan bir xil
bo'lsin; uz, ru va en matni alohida tasdiqlanadi:

```
Platforma nomi: tasdiqlash kodi XXXXXX. Uni hech kimga aytmang.
Platforma nomi: код подтверждения XXXXXX. Никому его не сообщайте.
Platforma nomi: your code is XXXXXX. Do not share it with anyone.
```

Tasdiqlangach parolni `backend/.env`ga serverda yozing (chatga yozmang):

```
ESKIZ_EMAIL=...
ESKIZ_PASSWORD=...
SMS_DRY_RUN=false
```

`SMS_DRY_RUN=true` bo'lsa SMS ketmaydi va markazni ochib bo'lmaydi: kod faqat logda ko'rinadi.

Sifat Edu o'z SMS'larini o'z nomidan yuborishi uchun shu hisobni kabinetda ham ulang («Markaz
sozlamalari» → «SMS (Eskiz)») va «Sifat Edu: tasdiqlash kodi …» shablonini ham tasdiqlating. Ulanmasa,
uning kirish kodlari platforma nomi bilan va oyiga 300 ta chegara bilan ketadi.

## 6. Sozlamalar va ochish

`backend/.env`:

```
PLATFORM_DOMAIN=example.uz
CENTERS_BASE_DOMAIN=example.uz
PLATFORM_NAME=Platforma nomi
PLATFORM_SUPPORT_PHONE=+998...
PLATFORM_SUPPORT_TELEGRAM=username
S3_CORS_ORIGINS=https://sifatedu.uz,https://*.example.uz
SIGNUP_OPEN=true
```

`frontend/.env`ga kerakli qiymatlarni `deploy.sh` shu fayldan o'zi yozadi.

```bash
bash /srv/sifatedu/infra/deploy/deploy.sh
```

Yopish kerak bo'lsa: `SIGNUP_OPEN=false` va yana `deploy.sh`. Ochilgan markazlar ishlayveradi.

## 7. Tekshiruv

1. `https://example.uz` — platforma sayti va tariflar.
2. «Markazni ochish»: forma, SMS kod, tayyorlanish (taxminan yarim daqiqa), kabinet.
3. `https://nom.example.uz` — yangi markaz sayti.
4. `https://example.uz/admin/` — super admin paneli: yangi markaz «Markazlar»da, ariza «Arizalar»da.

## Bilib qo'ying

- Narxlar va chegaralar — panelda «Tariflar». «Saytda ko'rinadi» belgisi olib tashlangan tarif
  platforma saytida chiqmaydi va uni tanlab bo'lmaydi.
- Bitta telefon raqamiga bitta markaz ochiladi.
- Tayyorlash uzilib qolsa (masalan, shu payt deploy bo'lsa), ariza 15 daqiqada «xato» bo'ladi va
  egasi qayta urina oladi.
- Markazlarning rasm va fayllari hozircha `media.sifatedu.uz` manzilidan beriladi (27-qadam).
- Domen hali tayyor bo'lmasa, `PLATFORM_DOMAIN=platform.sifatedu.uz` va
  `CENTERS_BASE_DOMAIN=sifatedu.uz` bilan ham ishlaydi, lekin `*.sifatedu.uz` sertifikati kerak
  bo'ladi va markazlar manzilida Sifat Edu domeni ko'rinadi.
