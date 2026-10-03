"""Avtomatik xabarlar va bot javoblari matni (3 tilda).

Til — foydalanuvchi tanlagan interfeys tili (`User.locale`).
"""

from datetime import date

MONTHS = {
    "uz": (
        "yanvar",
        "fevral",
        "mart",
        "aprel",
        "may",
        "iyun",
        "iyul",
        "avgust",
        "sentabr",
        "oktabr",
        "noyabr",
        "dekabr",
    ),
    "ru": (
        "января",
        "февраля",
        "марта",
        "апреля",
        "мая",
        "июня",
        "июля",
        "августа",
        "сентября",
        "октября",
        "ноября",
        "декабря",
    ),
    "en": (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ),
}

TEXTS: dict[str, dict[str, str]] = {
    "uz": {
        "inactive_3_title": "Darsni davom ettiramizmi?",
        "inactive_3_body": (
            "«{course}» kursida 3 kundan beri dars bo'lmadi. Keyingi dars: «{lesson}». "
            "Bugun 15 daqiqa ham oldinga siljitadi."
        ),
        "inactive_7_title": "Sizni kutyapmiz",
        "inactive_7_body": (
            "«{course}» kursida bir haftadan beri dars bo'lmadi. Qiyin bo'lsa, ustozga yozing — "
            "birga yechamiz. Keyingi dars: «{lesson}»."
        ),
        "live_day_title": "Jonli dars: {when}",
        "live_day_body": "«{group}» guruhi, {course}. {place}.",
        "live_soon_title": "Dars soat {time} da boshlanadi",
        "live_soon_body": "«{group}» guruhi, {course}. {place}.",
        "live_canceled_title": "Dars bekor qilindi: {when}",
        "live_canceled_body": "«{group}» guruhi, {course}. Sabab: {reason}",
        "live_absent_title": "Siz darsda bo'lmadingiz",
        "live_absent_body": (
            "{when}, «{group}» guruhi. Nima o'tilganini — izoh va yozuvni jadvalda ko'ring."
        ),
        "live_recording_title": "Dars yozuvi tayyor",
        "live_recording_body": "{when}, «{group}» guruhi. Jadvalda ko'ring.",
        "live_place_online": "Onlayn — «Qo'shilish» tugmasi jadvalda",
        "live_place_room": "Offlayn, {room}",
        "live_place_offline": "Offlayn",
        "live_no_reason": "ko'rsatilmagan",
        "lesson_opened_title": "Yangi dars ochildi: {lesson}",
        "lesson_opened_body": "«{group}» guruhi, {course}. Test va uy vazifasi tayyor.",
        "homework_new_title": "Yangi uy vazifasi: {student}",
        "homework_new_body": "«{course}» · {lesson}. Tekshirish uchun oching.",
        "homework_reviewed_title": "Uy vazifangiz tekshirildi",
        "homework_accepted_body": "«{lesson}»: qabul qilindi, baho — {score}/100.",
        "homework_returned_body": (
            "«{lesson}»: qayta ishlash kerak. O'qituvchi izohini o'qing va yangi javob yuboring."
        ),
        "payment_title": "To'lov qabul qilindi",
        "payment_body": "«{course}» kursi ochildi. Darslarni kabinetda boshlashingiz mumkin.",
        "receipt": "Chek: {url}",
        "opened_title": "Sizga kurs ochildi",
        "opened_body": "«{course}» kursi kabinetingizda. Omad!",
        "expiring_title": "To'lov muddati tugayapti",
        "expiring_body": (
            "«{course}» kursi uchun to'langan muddat {date} kuni tugaydi. Darslar to'xtab "
            "qolmasligi uchun keyingi oyga to'lang."
        ),
        "expired_title": "To'lov muddati tugadi",
        "expired_body": (
            "«{course}» kursi uchun to'langan muddat tugadi. Davom etish uchun to'lov qiling — "
            "savol bo'lsa, menejerimiz yordam beradi."
        ),
        "exam_draft_title": "Oylik imtihonni tayyorlang: {course}",
        "exam_draft_body": (
            "Imtihon {period} ochiladi. Admin'da 5 ta amaliy topshiriq va savollar modullarini "
            "kiriting, so'ng «Tayyor» qiling — tayyor bo'lmasa ochilmaydi."
        ),
        "placement_timeout_title": "⏳ Daraja testi vaqti tugadi — natijangiz {score}%",
        "placement_timeout_body": (
            "Sizga {percent}% chegirma kuponi berildi — {until} gacha amal qiladi (birinchi "
            "to'lovga). Menejerimiz siz bilan bog'lanadi; savolingiz bo'lsa — botga yozing."
        ),
        "coupon_first_title": "🎁 {percent}% chegirma kuponingiz kutyapti",
        "coupon_last_title": "⏳ {percent}% chegirma kuponi tugayapti",
        "coupon_body": (
            "Kupon {until} gacha amal qiladi (birinchi to'lovga). Kursga yozilish uchun "
            "menejerimiz bilan bog'laning yoki botda savolingizni yozing."
        ),
        "exam_opened_title": "Oylik imtihon ochildi: {course}",
        "exam_opened_body": (
            "{period}. Test — {count} savol, {minutes} daqiqa, bitta urinish (saytda yoki botda); "
            "amaliy — {tasks} ta topshiriq saytda."
        ),
        "exam_result_title": "Imtihon natijasi: {course}",
        "exam_result_body": "Natija — {total}%, {status}. Test {test}%, amaliy {practical}%.",
        "exam_passed": "o'tdingiz 🎉",
        "exam_failed": "bu safar o'tmadi — keyingi oy albatta o'tasiz",
        "certificate_title": "🎓 Sertifikat tayyor: {course}",
        "certificate_body": (
            "Tabriklaymiz! Sertifikat raqami: {number}. Kabinetda ko'ring, ulashing yoki PDF "
            "sifatida saqlang."
        ),
        "referral_lesson_title": "🎁 +{coins} coin: {friend} birinchi darsni tugatdi",
        "referral_lesson_body": (
            "Siz taklif qilgan do'stingiz o'qishni boshladi. Coinlarni do'konda sovg'aga "
            "almashtirishingiz mumkin."
        ),
        "referral_paid_title": "🎁 +{coins} coin va {percent}% kupon: {friend} to'lov qildi",
        "referral_paid_body": (
            "Rahmat! Kupon keyingi to'lovingizda o'zi qo'llanadi. Yana do'stlaringizni taklif "
            "qiling."
        ),
        "shop_new_title": "🛍 Do'kondan yangi buyurtma: {name}",
        "shop_new_body": "{student} — {price} coin. Tayyorlab, holatini admin'da belgilang.",
        "shop_status_title": "🛍 {name}: {status}",
        "shop_ready_body": "Sovg'angiz tayyor — olib ketishingiz mumkin.",
        "shop_delivered_body": "Sovg'a topshirildi. Yoqimli foydalaning!",
        "shop_canceled_body": "Buyurtma bekor qilindi, {price} coin hisobingizga qaytdi.",
        "open": "Ochish",
        "start_quiz": "📝 Testni boshlash",
        "test": "Sinov",
        "linked": (
            "✅ Telegram ulandi. Endi darslar, to'lovlar va yangiliklar haqidagi xabarlar shu "
            "yerga keladi.\n\nSavolingiz bo'lsa, shu yerga yozing — AI maslahatchi javob beradi."
        ),
        "link_expired": (
            "Havola eskirgan yoki allaqachon ishlatilgan. Saytda Sozlamalar → «Telegram'ni "
            "ulash» tugmasini qayta bosing."
        ),
        "link_taken": (
            "Bu Telegram boshqa Sifat Edu akkauntiga ulangan. Yordam kerak bo'lsa, "
            "menejerga yozing."
        ),
    },
    "ru": {
        "inactive_3_title": "Продолжим обучение?",
        "inactive_3_body": (
            "По курсу «{course}» уже 3 дня не было занятий. Следующий урок: «{lesson}». "
            "Даже 15 минут сегодня — это шаг вперёд."
        ),
        "inactive_7_title": "Мы вас ждём",
        "inactive_7_body": (
            "По курсу «{course}» неделю не было занятий. Если трудно, напишите преподавателю — "
            "разберёмся вместе. Следующий урок: «{lesson}»."
        ),
        "live_day_title": "Онлайн-урок: {when}",
        "live_day_body": "Группа «{group}», {course}. {place}.",
        "live_soon_title": "Урок начнётся в {time}",
        "live_soon_body": "Группа «{group}», {course}. {place}.",
        "live_canceled_title": "Урок отменён: {when}",
        "live_canceled_body": "Группа «{group}», {course}. Причина: {reason}",
        "live_absent_title": "Вы пропустили урок",
        "live_absent_body": (
            "{when}, группа «{group}». Что прошли — комментарий и запись в расписании."
        ),
        "live_recording_title": "Запись урока готова",
        "live_recording_body": "{when}, группа «{group}». Смотрите в расписании.",
        "live_place_online": "Онлайн — кнопка «Подключиться» в расписании",
        "live_place_room": "Офлайн, {room}",
        "live_place_offline": "Офлайн",
        "live_no_reason": "не указана",
        "lesson_opened_title": "Открыт новый урок: {lesson}",
        "lesson_opened_body": "Группа «{group}», {course}. Тест и домашнее задание готовы.",
        "homework_new_title": "Новое домашнее задание: {student}",
        "homework_new_body": "«{course}» · {lesson}. Откройте, чтобы проверить.",
        "homework_reviewed_title": "Домашнее задание проверено",
        "homework_accepted_body": "«{lesson}»: принято, оценка — {score}/100.",
        "homework_returned_body": (
            "«{lesson}»: нужно доработать. Прочитайте комментарий преподавателя и отправьте "
            "новый ответ."
        ),
        "payment_title": "Оплата получена",
        "payment_body": "Курс «{course}» открыт. Можно начинать занятия в личном кабинете.",
        "receipt": "Чек: {url}",
        "opened_title": "Вам открыт курс",
        "opened_body": "Курс «{course}» уже в вашем кабинете. Удачи!",
        "expiring_title": "Оплаченный период заканчивается",
        "expiring_body": (
            "Оплаченный период по курсу «{course}» заканчивается {date}. Чтобы занятия не "
            "прерывались, оплатите следующий месяц."
        ),
        "expired_title": "Оплаченный период закончился",
        "expired_body": (
            "Оплаченный период по курсу «{course}» закончился. Чтобы продолжить, оплатите "
            "обучение — если есть вопросы, менеджер поможет."
        ),
        "exam_draft_title": "Подготовьте ежемесячный экзамен: {course}",
        "exam_draft_body": (
            "Экзамен откроется {period}. В админке добавьте 5 практических заданий и модули для "
            "вопросов, затем отметьте «Готов» — иначе он не откроется."
        ),
        "placement_timeout_title": "⏳ Время теста на уровень вышло — ваш результат {score}%",
        "placement_timeout_body": (
            "Вам выдан купон на скидку {percent}% — действует до {until} (на первую оплату). "
            "Менеджер свяжется с вами; если есть вопрос — напишите в бот."
        ),
        "coupon_first_title": "🎁 Ваш купон на скидку {percent}% ждёт вас",
        "coupon_last_title": "⏳ Купон на скидку {percent}% скоро сгорит",
        "coupon_body": (
            "Купон действует до {until} (на первую оплату). Чтобы записаться на курс, свяжитесь с "
            "менеджером или напишите вопрос в боте."
        ),
        "exam_opened_title": "Ежемесячный экзамен открыт: {course}",
        "exam_opened_body": (
            "{period}. Тест — {count} вопросов, {minutes} минут, одна попытка (на сайте или в "
            "боте); практика — {tasks} заданий на сайте."
        ),
        "exam_result_title": "Результат экзамена: {course}",
        "exam_result_body": "Результат — {total}%, {status}. Тест {test}%, практика {practical}%.",
        "exam_passed": "вы сдали 🎉",
        "exam_failed": "в этот раз не получилось — в следующем месяце обязательно сдадите",
        "certificate_title": "🎓 Сертификат готов: {course}",
        "certificate_body": (
            "Поздравляем! Номер сертификата: {number}. Смотрите в кабинете, делитесь или "
            "сохраните как PDF."
        ),
        "referral_lesson_title": "🎁 +{coins} монет: {friend} завершил(а) первый урок",
        "referral_lesson_body": (
            "Приглашённый вами друг начал учиться. Монеты можно обменять на подарки в магазине."
        ),
        "referral_paid_title": "🎁 +{coins} монет и купон {percent}%: {friend} оплатил(а) курс",
        "referral_paid_body": (
            "Спасибо! Купон применится к вашей следующей оплате автоматически. Приглашайте ещё."
        ),
        "shop_new_title": "🛍 Новый заказ в магазине: {name}",
        "shop_new_body": "{student} — {price} монет. Подготовьте и отметьте статус в админке.",
        "shop_status_title": "🛍 {name}: {status}",
        "shop_ready_body": "Ваш подарок готов — можно забирать.",
        "shop_delivered_body": "Подарок вручён. Пользуйтесь с удовольствием!",
        "shop_canceled_body": "Заказ отменён, {price} монет вернулись на ваш счёт.",
        "open": "Открыть",
        "start_quiz": "📝 Начать тест",
        "test": "Тест",
        "linked": (
            "✅ Telegram подключён. Теперь сообщения о занятиях, оплатах и новостях будут "
            "приходить сюда.\n\nЕсли есть вопрос, напишите здесь — ответит ИИ-консультант."
        ),
        "link_expired": (
            "Ссылка устарела или уже использована. На сайте откройте Настройки и снова "
            "нажмите «Подключить Telegram»."
        ),
        "link_taken": (
            "Этот Telegram уже подключён к другому аккаунту Sifat Edu. Если нужна помощь, "
            "напишите менеджеру."
        ),
    },
    "en": {
        "inactive_3_title": "Shall we continue?",
        "inactive_3_body": (
            "No lessons in «{course}» for 3 days. Next lesson: «{lesson}». Even 15 minutes "
            "today moves you forward."
        ),
        "inactive_7_title": "We are waiting for you",
        "inactive_7_body": (
            "No lessons in «{course}» for a week. If it is hard, write to your teacher — we will "
            "sort it out together. Next lesson: «{lesson}»."
        ),
        "live_day_title": "Live lesson: {when}",
        "live_day_body": "Group «{group}», {course}. {place}.",
        "live_soon_title": "The lesson starts at {time}",
        "live_soon_body": "Group «{group}», {course}. {place}.",
        "live_canceled_title": "Lesson cancelled: {when}",
        "live_canceled_body": "Group «{group}», {course}. Reason: {reason}",
        "live_absent_title": "You missed the lesson",
        "live_absent_body": (
            "{when}, group «{group}». See what was covered — notes and recording in the schedule."
        ),
        "live_recording_title": "The lesson recording is ready",
        "live_recording_body": "{when}, group «{group}». See it in the schedule.",
        "live_place_online": "Online — the «Join» button is in the schedule",
        "live_place_room": "In class, {room}",
        "live_place_offline": "In class",
        "live_no_reason": "not given",
        "lesson_opened_title": "New lesson unlocked: {lesson}",
        "lesson_opened_body": "Group «{group}», {course}. The quiz and homework are ready.",
        "homework_new_title": "New homework: {student}",
        "homework_new_body": "«{course}» · {lesson}. Open it to review.",
        "homework_reviewed_title": "Your homework was reviewed",
        "homework_accepted_body": "«{lesson}»: accepted, score {score}/100.",
        "homework_returned_body": (
            "«{lesson}»: needs changes. Read the teacher's comment and send a new answer."
        ),
        "payment_title": "Payment received",
        "payment_body": (
            "The «{course}» course is open. You can start the lessons in your dashboard."
        ),
        "receipt": "Receipt: {url}",
        "opened_title": "A course was opened for you",
        "opened_body": "The «{course}» course is in your dashboard. Good luck!",
        "expiring_title": "Your paid period is ending",
        "expiring_body": (
            "The paid period for «{course}» ends on {date}. Pay for the next month so your "
            "lessons are not interrupted."
        ),
        "expired_title": "Your paid period has ended",
        "expired_body": (
            "The paid period for «{course}» has ended. Pay to continue — our manager will "
            "help if you have questions."
        ),
        "exam_draft_title": "Prepare the monthly exam: {course}",
        "exam_draft_body": (
            "The exam opens {period}. In the admin, add 5 practical tasks and the modules for "
            "questions, then mark it «Ready» — otherwise it will not open."
        ),
        "placement_timeout_title": "⏳ Level test time is up — your result is {score}%",
        "placement_timeout_body": (
            "You got a {percent}% discount coupon — valid until {until} (for the first "
            "payment). Our manager will contact you; if you have a question, write to the bot."
        ),
        "coupon_first_title": "🎁 Your {percent}% discount coupon is waiting",
        "coupon_last_title": "⏳ Your {percent}% discount coupon is expiring",
        "coupon_body": (
            "The coupon is valid until {until} (for the first payment). To enrol, contact our "
            "manager or ask your question in the bot."
        ),
        "exam_opened_title": "Monthly exam is open: {course}",
        "exam_opened_body": (
            "{period}. Quiz — {count} questions, {minutes} minutes, one attempt (on the website or "
            "in the bot); practice — {tasks} tasks on the website."
        ),
        "exam_result_title": "Exam result: {course}",
        "exam_result_body": "Result — {total}%, {status}. Quiz {test}%, practice {practical}%.",
        "exam_passed": "you passed 🎉",
        "exam_failed": "not this time — you will pass next month",
        "certificate_title": "🎓 Certificate ready: {course}",
        "certificate_body": (
            "Congratulations! Certificate number: {number}. See it in your dashboard, share it or "
            "save it as a PDF."
        ),
        "referral_lesson_title": "🎁 +{coins} coins: {friend} finished the first lesson",
        "referral_lesson_body": (
            "The friend you invited has started learning. Spend coins on gifts in the shop."
        ),
        "referral_paid_title": "🎁 +{coins} coins and a {percent}% coupon: {friend} paid",
        "referral_paid_body": (
            "Thank you! The coupon applies to your next payment automatically. Invite more friends."
        ),
        "shop_new_title": "🛍 New shop order: {name}",
        "shop_new_body": "{student} — {price} coins. Prepare it and set the status in the admin.",
        "shop_status_title": "🛍 {name}: {status}",
        "shop_ready_body": "Your gift is ready — you can pick it up.",
        "shop_delivered_body": "The gift has been handed over. Enjoy!",
        "shop_canceled_body": "The order was canceled, {price} coins are back in your account.",
        "open": "Open",
        "start_quiz": "📝 Start the quiz",
        "test": "Test",
        "linked": (
            "✅ Telegram is connected. Messages about lessons, payments and news will now "
            "arrive here.\n\nIf you have a question, write here — the AI advisor will answer."
        ),
        "link_expired": (
            "The link has expired or was already used. On the site, open Settings and press "
            "“Connect Telegram” again."
        ),
        "link_taken": (
            "This Telegram is already connected to another Sifat Edu account. Write to a "
            "manager if you need help."
        ),
    },
}


def locale_of(value: str | None) -> str:
    code = (value or "")[:2].lower()
    return code if code in TEXTS else "uz"


def text(locale: str | None, key: str, **params: str) -> str:
    template = TEXTS[locale_of(locale)][key]
    return template.format(**params) if params else template


def day_month(value: date, locale: str | None) -> str:
    """5-oktabr / 5 октября / October 5."""
    code = locale_of(locale)
    month = MONTHS[code][value.month - 1]
    if code == "uz":
        return f"{value.day}-{month}"
    if code == "ru":
        return f"{value.day} {month}"
    return f"{month} {value.day}"
