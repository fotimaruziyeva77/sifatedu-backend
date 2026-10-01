# Backup va tiklash

**Nima saqlanadi:** PostgreSQL bazasi (foydalanuvchilar, kurslar, buyurtmalar, progress).
Videolar va rasmlar object storage'da turadi — ular uchun provayderda **versiyalash**
(bucket versioning) yoqiladi, bu yerda nusxalanmaydi.

**Qachon:** har kuni `BACKUP_HOUR` da (standart 03:00, Toshkent vaqti). Konteyner birinchi
marta ishga tushganda nusxa bo'lmasa, darhol bittasi olinadi. RPO — 24 soat.

**Qayerda:** `BACKUP_DIR` (standart `./backups`), 30 kun (`BACKUP_KEEP_DAYS`). `BACKUP_S3_BUCKET`
berilsa, har bir nusxa boshqa joyga — S3-mos bucket'ga ham yuklanadi (serverdan tashqarida
saqlash uchun tavsiya etiladi).

Har bir nusxa yozilgach `pg_restore --list` bilan tekshiriladi. Oxirgi nusxa 26 soatdan eski
bo'lsa, `backup` konteyneri `unhealthy` bo'ladi.

## Qo'lda backup

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backup backup.sh
```

## Tiklash (RTO ≤ 4 soat)

```bash
# 1. Ilovani to'xtatish
docker compose -f docker-compose.yml -f docker-compose.prod.yml stop backend worker worker-video beat
# 2. Kerakli nusxani tanlash
ls -lh backups/
# 3. Tiklash
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm backup \
    restore.sh /backups/sifatedu_2026-09-27_0300.dump
# 4. Ilovani yoqish (migratsiyalar avtomatik)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

**Har oy tiklash sinovi** (TZ talabi): oxirgi nusxani alohida bazaga tiklab, jadvallar va
yozuvlar sonini tekshiring — backup faqat tiklanganda qadrli.
