"""Kunlik test: bugungi holat va hozir yuborish — barcha o'qiyotgan guruhlar.

Serverda, /srv/sifatedu papkasida (kod Django shell'ga uzatiladi, image qayta yig'ilmaydi):

  S=backend/scripts/kunlik_test.py
  dc exec -T -e ACTION=status backend python manage.py shell < $S
  dc exec -T -e ACTION=send   backend python manage.py shell < $S

status — har o'qiyotgan guruh: o'quvchilar, savollar banki, bugungi test, kim boshladi va tugatdi.
send   — bugungi testni hozir yuboradi (07:00 dagidek): testi yo'q guruhlarga ochadi; ertalab
         savol yetmagani uchun berilmagan test bank endi yetarli bo'lsa ochiladi; xabar (sayt va
         Telegram) uni hali olmagan o'quvchilarga boradi. Faqat 07:00–23:00 orasida; qayta
         ishga tushirilsa, hech kimga ikkinchi marta bormaydi.
"""

import os

from django.utils import timezone

from apps.dailytest import services as daily
from apps.dailytest.models import DailyTest
from apps.learning.models import StudyGroup
from apps.live.services import members
from apps.notifications.models import Notification
from apps.rewards import services as rewards

ACTION = os.environ.get("ACTION", "status")


def status() -> None:
    now = timezone.now()
    day = daily.local_day(now)
    config = rewards.settings()
    state = "yoqilgan" if config.daily_test else "o'chirilgan"
    print(
        f"{day:%d.%m.%Y}, soat {timezone.localtime(now):%H:%M}. Kunlik test: {state}, "
        f"{config.daily_test_questions} ta savol."
    )
    tests = {test.group_id: test for test in DailyTest.objects.filter(day=day)}
    groups = StudyGroup.objects.filter(status=StudyGroup.Status.ACTIVE).order_by("name")
    if not groups.exists():
        print("«O'qiyapti» holatidagi guruh yo'q.")
        return
    for group in groups:
        people = members(group.pk, now=now).count()
        size = len(daily.pool(group))
        test = tests.get(group.pk)
        if test is None:
            today = "bugun test yo'q"
        else:
            started = test.attempts.count()
            done = test.attempts.filter(finished_at__isnull=False).count()
            today = f"bugun: {test.get_status_display()}, boshladi {started}, tugatdi {done}"
        print(f"- {group.name}: {people} o'quvchi, bankda {size} ta savol — {today}")


def send() -> None:
    now = timezone.now()
    clock = timezone.localtime(now).time()
    if not daily.OPEN_AT <= clock < daily.CLOSE_AT:
        raise SystemExit(f"Hozir soat {clock:%H:%M}: kunlik test 07:00 dan 23:00 gacha yuboriladi.")
    if not rewards.settings().daily_test:
        raise SystemExit(
            "Kunlik test o'chirilgan: admin → XP va coin → Sozlamalar → «Kunlik test»."
        )
    day = daily.local_day(now)
    sent_before = Notification.objects.filter(kind=Notification.Kind.DAILY_TEST).count()

    # Ertalab savol yetmay berilmagan test — bank endi yetarli bo'lsa, ochiladi.
    skipped = DailyTest.objects.filter(
        day=day, status=DailyTest.Status.SKIPPED, group__status=StudyGroup.Status.ACTIVE
    ).select_related("group")
    for test in skipped:
        size = len(daily.pool(test.group))
        if size >= test.questions_count:
            test.pool_size = size
            test.status = DailyTest.Status.OPEN
            test.save(update_fields=["pool_size", "status", "updated_at"])

    # Testi yo'q guruhlar — 07:00 dagidek (savol yetmasa — o'qituvchiga eslatma).
    daily.open_day(now=now)

    # Ochiq testlar: xabar hali bormagan o'quvchilarga (keyin qo'shilganlarga ham).
    opened = DailyTest.objects.filter(
        day=day, status=DailyTest.Status.OPEN, group__status=StudyGroup.Status.ACTIVE
    )
    for test in opened.select_related("group"):
        for student in members(test.group_id, now=now):
            daily.announce(test, student)

    sent = Notification.objects.filter(kind=Notification.Kind.DAILY_TEST).count() - sent_before
    print(f"Xabar yuborildi: {sent} ta o'quvchiga.\n")
    status()


if ACTION == "status":
    status()
elif ACTION == "send":
    send()
else:
    raise SystemExit(f"Noma'lum ACTION={ACTION}: status yoki send.")
