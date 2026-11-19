"""SMM agent holati: `dc exec -T backend python manage.py tenant_command shell --schema=sifat < infra/tools/smm_check.py`
Maxfiy qiymatlar (token) chiqarilmaydi."""
from django.conf import settings as dj
from apps.notifications import telegram
from apps.smm import review
from apps.smm.models import Post, SmmSettings

s = SmmSettings.load()
print("== Sozlamalar")
print("yoqilgan:", s.enabled, "| tasdiqsiz:", s.auto_publish, "| kanal:", repr(s.channel), "| soat:", s.publish_hour)
print("faktlar qatorlari:", len([x for x in s.about.splitlines() if x.strip()]))
print("instagram:", s.instagram, "| ig_user:", s.ig_username or "-", "| ig_xato:", s.ig_error or "-")
print("model:", dj.SMM_GEMINI_MODEL, "| gemini kalit bor:", bool(getattr(dj, "GEMINI_API_KEY", "")))
print("== Tasdiqlovchilar (Telegram ulangan):", len(review.approvers()))
if s.channel:
    try:
        me = telegram.call("getMe", {})["id"]
        m = telegram.call("getChatMember", {"chat_id": s.channel, "user_id": me})
        print("== Kanal: bot holati:", m.get("status"), "| yozish:", m.get("can_post_messages"))
    except Exception as e:
        print("== Kanal tekshirilmadi:", type(e).__name__, str(e)[:200])
print("== Postlar")
for p in Post.objects.order_by("publish_at")[:15]:
    print(p.pk, p.publish_at.strftime("%m-%d %H:%M"), p.kind, p.status, "|", (p.topic or "")[:40], "|", (p.error or "")[:120])
print("jami:", Post.objects.count())
