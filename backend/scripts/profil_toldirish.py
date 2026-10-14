"""Hozirgi o'quvchilarga bir martalik «Profilni to'ldiring» taklifi (22d).

Guruhda o'qiyotgan, to'liq ismi tasdiqlanmagan yoki tug'ilgan sanasi yo'q o'quvchilarga botda
«✍️ Profilni to'ldirish» tugmali xabar boradi. Tugma bosilsa — familiya, ism, otasining ismi,
tug'ilgan sana va selfi so'raladi. Bir marta: qayta ishga tushirilsa, oldin yuborilganlarga
yubormaydi (yangi qo'shilganlarga yuboradi).

Serverda, /srv/sifatedu papkasida (kod Django shell'ga uzatiladi, image qayta yig'ilmaydi):

  S=backend/scripts/profil_toldirish.py
  dc exec -T -e ACTION=status backend python manage.py shell < $S
  dc exec -T -e ACTION=send backend python manage.py shell < $S

status — guruh o'quvchilari: nechtasi to'ldirgan, nechtasi rasm yuborgan, kimga bot orqali
         yetib boradi, kimning Telegram'i ulanmagan (ularni o'qituvchi kabinetda to'ldiradi).
send   — to'ldirmagan va Telegram'i ulanganlarga taklif (soniyasiga ~10 ta).
"""

import os
import time

from apps.bot import profile as flow
from apps.learning.models import Enrollment
from apps.users import profile as person
from apps.users.models import User

ACTION = os.environ.get("ACTION", "status")

students = (
    User.objects.filter(
        is_active=True,
        enrollments__status=Enrollment.Status.ACTIVE,
        enrollments__group__isnull=False,
    )
    .distinct()
    .order_by("last_name", "first_name")
)
done = [user for user in students if person.complete(user)]
todo = [user for user in students if not person.complete(user)]
reachable = [user for user in todo if flow.chat_of(user) is not None]
offline = [user for user in todo if flow.chat_of(user) is None]

print(f"Guruh o'quvchilari: {len(students)}")
print(f"  to'ldirgan: {len(done)} (rasm bilan: {sum(1 for user in done if user.avatar)})")
print(f"  to'ldirmagan: {len(todo)}")
print(f"    botga yetadi: {len(reachable)}, Telegram yo'q: {len(offline)}")
for user in offline:
    print(f"    Telegram yo'q: {user.get_full_name() or '—'} {user.phone}")

if ACTION == "send":
    sent = skipped = 0
    for user in reachable:
        if flow.push(user):
            sent += 1
            time.sleep(0.1)
        else:
            skipped += 1
    print(f"Yuborildi: {sent}; oldin yuborilgan yoki yetmadi: {skipped}")
elif ACTION != "status":
    print("ACTION=status yoki ACTION=send")
