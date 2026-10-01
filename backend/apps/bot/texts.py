"""Bot matnlari (3 tilda). Til — botda tanlangani (`BotChat.language`)."""

LANGUAGES = {"uz": "🇺🇿 O'zbekcha", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}
CHOOSE_LANGUAGE = "Tilni tanlang · Выберите язык · Choose a language"

TEXTS: dict[str, dict[str, str]] = {
    "uz": {
        "subscribe": (
            "Botdan foydalanish uchun kanalimizga obuna bo'ling, so'ng «✅ Obuna bo'ldim» "
            "tugmasini bosing."
        ),
        "btn_subscribed": "✅ Obuna bo'ldim",
        "not_subscribed": "Hali obuna bo'lmadingiz. Kanalga qo'shiling va qayta bosing.",
        "welcome": (
            "Assalomu alaykum{name}! Sifat Edu botiga xush kelibsiz.\n\n"
            "Bu yerda dars testlarini ishlaysiz, jadvalni ko'rasiz, yangiliklarni olasiz, "
            "savollaringizga esa AI maslahatchi javob beradi.\n\n"
            "Ro'yxatdan o'tish uchun «📱 Telefonni yuborish» tugmasini bosing — SMS kerak emas."
        ),
        "terms": (
            'Tugmani bosib, <a href="{offer}">ommaviy oferta</a> va '
            '<a href="{privacy}">maxfiylik siyosati</a>ga rozilik bildirasiz.'
        ),
        "welcome_back": "Xush kelibsiz{name}! Kerakli bo'limni menyudan tanlang.",
        "btn_contact": "📱 Telefonni yuborish",
        "btn_courses": "📚 Kurslarim",
        "btn_tests": "📝 Testlar",
        "btn_schedule": "📅 Jadval",
        "btn_invite": "🎁 Do'stni taklif qilish",
        "btn_ask": "💬 Savol berish",
        "btn_settings": "⚙️ Sozlamalar",
        "not_own": (
            "Iltimos, o'zingizning raqamingizni «📱 Telefonni yuborish» tugmasi bilan yuboring."
        ),
        "only_uz": "Hozircha faqat O'zbekiston raqamlari (+998) bilan ro'yxatdan o'tish mumkin.",
        "staff_contact": (
            "Bu raqam xodim akkauntiga tegishli. Xodim Telegram'ni saytdagi kabinetdan "
            "«Telegram'ni ulash» tugmasi orqali ulaydi."
        ),
        "account_blocked": "Bu akkaunt bloklangan. Qo'llab-quvvatlash bilan bog'laning.",
        "registered": (
            "🎉 Akkaunt ochildi! Video darslar saytda: «🖥 Saytga kirish» tugmasi sizni "
            "parolsiz kiritadi."
        ),
        "linked": "✅ Telegram akkauntingizga ulandi{name}!",
        "need_account": (
            "Buning uchun avval ro'yxatdan o'ting: «📱 Telefonni yuborish» tugmasini bosing."
        ),
        "ask": (
            "Savolingizni yozing — AI maslahatchi javob beradi. Kurslar, narxlar, qaysi yo'nalish "
            "sizga mosligi haqida so'rashingiz mumkin."
        ),
        "help": (
            "/menu — menyu\n/tests — testlar\n/schedule — jadval\n/settings — sozlamalar\n\n"
            "Istalgan savolni yozing — AI maslahatchi javob beradi."
        ),
        "courses_title": "📚 <b>Kurslaringiz</b>",
        "course_line": "<b>{title}</b> — {percent}% ({done}/{total})\nKeyingi dars: {lesson}",
        "course_done": "<b>{title}</b> — tugatilgan ✅",
        "no_courses": (
            "Sizda hali kurs yo'q. Kurslar bilan saytda tanishing yoki savol yozing — AI "
            "maslahatchi mos kursni tanlashga yordam beradi."
        ),
        "btn_catalog": "📚 Kurslar katalogi",
        "tests_title": "📝 <b>Testlar</b>",
        "tests_open": "Ishlash mumkin bo'lgan testlar:",
        "tests_line": "• {lesson} — {course}",
        "tests_empty": (
            "Hozircha yangi test yo'q. Keyingi dars videosini saytda ko'ring — testi shu yerda "
            "chiqadi."
        ),
        "tests_passed": "O'tilgan testlar: {count}",
        "btn_quiz_resume": "▶️ {lesson}",
        "schedule_title": "📅 <b>Yaqin darslar</b>",
        "schedule_empty": "Yaqin kunlarda jonli dars yo'q.",
        "schedule_no_group": (
            "Siz hali guruhga qo'shilmagansiz — jadval guruhga qo'shilgach chiqadi."
        ),
        "schedule_line": "<b>{when}</b>\n{course} · {group} · {place}",
        "schedule_topic": "Mavzu: {topic}",
        "schedule_canceled": "❌ Bekor qilindi: {reason}",
        "schedule_join_hint": "«Qo'shilish» tugmasi dars boshlanishidan 15 daqiqa oldin chiqadi.",
        "btn_join": "🔗 Qo'shilish · {time}",
        "invite": (
            "🎁 <b>Do'stlaringizni taklif qiling</b>\n\n"
            "Havolangiz (bot):\n{bot}\n\nSayt orqali:\n{site}\n\n"
            "Taklif qilganlaringiz: <b>{count}</b>."
        ),
        "invite_rewards": "<b>Mukofotlar</b>",
        "invite_lesson": "🪙 Do'stingiz birinchi darsni tugatsa — <b>+{coins} coin</b>",
        "invite_paid": "💳 Do'stingiz to'lov qilsa — <b>{reward}</b>",
        "invite_coins": "+{coins} coin",
        "invite_coupon": "{percent}% kupon",
        "invite_and": " va ",
        "invite_discount": "🎉 Do'stingizga birinchi to'lovda <b>{percent}% chegirma</b>",
        "btn_share": "📤 Do'stlarga yuborish",
        "share_text": "Sifat Edu'da IT o'rganyapman — sen ham qo'shil!",
        "settings": "⚙️ <b>Sozlamalar</b>\n\nTil: {language}\nYangiliklar: {news}",
        "news_on": "yoqilgan ✅",
        "news_off": "o'chirilgan",
        "btn_language": "🌐 Tilni o'zgartirish",
        "btn_news_off": "🔕 Yangiliklarni o'chirish",
        "btn_news_on": "🔔 Yangiliklarni yoqish",
        "btn_site": "🖥 Saytga kirish",
        "news_muted": "Yangiliklar o'chirildi. Qayta yoqish: ⚙️ Sozlamalar.",
        "news_enabled": "Yangiliklar yoqildi.",
        "quiz_intro": (
            "📝 <b>{title}</b>\n{lesson}\n\n{count} ta savol · o'tish uchun {percent}%.\n"
            "Har javobdan keyin to'g'ri yoki noto'g'riligi chiqadi, to'g'ri javoblar esa test "
            "o'tilgach ko'rsatiladi."
        ),
        "quiz_resume": "Testni davom ettiramiz: <b>{title}</b>",
        "quiz_missing": "Test topilmadi yoki unda hali savol yo'q.",
        "quiz_no_access": "Bu kurs sizga ochiq emas.",
        "quiz_locked": "Bu dars hali yopiq: avval «{lesson}» darsining testidan o'ting.",
        "quiz_offline_locked": "Bu darsning testi ustoz darsni o'tgach ochiladi.",
        "q_head": "<b>{index}/{total}.</b> {text}",
        "q_single_hint": "Bitta javobni tanlang:",
        "q_multiple_hint": "Bir nechta to'g'ri javob bor — belgilab, «✅ Tayyor»ni bosing:",
        "q_text_hint": "✍️ Javobni yozib yuboring.",
        "q_order_hint": "To'g'ri tartibda bosing — birinchisidan boshlab:",
        "q_order_chosen": "Tartib: {items}",
        "q_match_hint": "Chapdagi har biriga mos javobni tanlang:",
        "q_match_prompt": "«{item}» → ?",
        "btn_done": "✅ Tayyor",
        "btn_reset": "↩️ Qaytadan",
        "q_right": "✅ To'g'ri",
        "q_wrong": "❌ Noto'g'ri",
        "q_your": "Javobingiz: {answer}",
        "q_pick_one": "Kamida bitta javobni belgilang.",
        "q_stale": "Bu savol yopilgan — oxirgi savolga javob bering.",
        "result_pass": "🎉 <b>Test topshirildi!</b>\nNatija: {score}% ({correct}/{total}) {stars}",
        "result_fail": (
            "😕 Natija: {score}% ({correct}/{total}). O'tish uchun {percent}% kerak.\n\n"
            "Videoni qayta ko'rib, qayta urinib ko'ring."
        ),
        "review_title": "<b>Xatolar ustida ishlash</b>",
        "review_all_right": "Barcha javoblar to'g'ri! 👏",
        "review_item": "❌ <b>{index}.</b> {question}\nSiz: {yours}\nTo'g'ri javob: {right}",
        "review_note": "💡 {text}",
        "btn_next_lesson": "▶️ Keyingi darsga",
        "btn_course": "📚 Kursga qaytish",
        "btn_retry": "🔁 Qayta urinish",
        "btn_video": "🎬 Videoni ko'rish",
        "btn_open": "Ochish",
        "no_answer": "javob yo'q",
        "btn_today": "✅ Bugungi topshiriqlar",
        "today_title": "✅ <b>Bugungi topshiriqlar</b>",
        "today_lesson": "Darsni ko'ring: {title}",
        "today_quiz": "Testdan o'ting: {title}",
        "today_review": "Botda takrorlang: 5 ta savol",
        "today_homework": "Uy vazifasini topshiring: {title}",
        "today_live": "Darsga vaqtida keling: {title}",
        "today_done": "🎉 Hammasi bajarildi! Ertaga — yangi topshiriqlar.",
        "today_empty": "Bugun topshiriq yo'q. Topshiriqlar har kuni 09:00 da beriladi.",
        "today_morning": (
            "☀️ Xayrli tong! Bugun uchta topshiriq — bajarsangiz, seriyangiz davom etadi."
        ),
        "btn_today_lesson": "▶️ Darsni ochish",
        "btn_today_quiz": "📝 Testni boshlash",
        "btn_today_review": "🔁 Takrorlash",
        "btn_today_homework": "📎 Vazifani ochish",
        "btn_today_live": "📅 Jadval",
        "review_intro": (
            "🔁 <b>Takrorlash</b>: o'tilgan testlardan {count} ta savol. Har javobdan keyin — "
            "to'g'ri yoki noto'g'ri."
        ),
        "review_empty": "Takrorlash uchun hali o'tilgan test yo'q — avval dars testidan o'ting.",
        "review_done": "🔁 Takrorlash tugadi: {correct}/{total} to'g'ri.",
        "winners_title": "🏆 <b>Haftaning eng faol o'quvchilari</b>",
        "winners_footer": "Tabriklaymiz! Yangi hafta — yangi imkoniyat 💪",
        "tests_exam": "🏆 <b>Oylik imtihon ochiq</b>: {course}",
        "btn_exam": "🏆 Oylik imtihon: {course}",
        "exam_intro": (
            "🏆 <b>Oylik imtihon</b> — {course}\n\n{count} savol · {minutes} daqiqa · bitta "
            "urinish. Vaqt «Boshlash» bosilganda boshlanadi.\nJavoblar to'g'ri yoki noto'g'riligi "
            "imtihon yopilgach ko'rsatiladi. Amaliy topshiriqlar — saytda."
        ),
        "btn_exam_start": "▶️ Boshlash",
        "btn_exam_tasks": "🖥 Amaliy topshiriqlar",
        "exam_time_left": "⏳ {minutes} daqiqa qoldi",
        "exam_saved": "✔️ Javob saqlandi",
        "exam_done": (
            "✅ <b>Test qismi yakunlandi</b>: {score}%.\nTo'g'ri javoblar imtihon yopilgach "
            "ko'rsatiladi. Amaliy topshiriqlarni saytda topshiring."
        ),
        "exam_closed": "Imtihon hozir ochiq emas.",
        "exam_already": "Imtihon testini topshirgansiz: {score}%. Amaliy topshiriqlar — saytda.",
        "only_text": "Hozircha faqat matnli xabarlarni tushunaman — savolingizni yozib yuboring.",
        "site_hint": "Video darslar va kabinet — saytda 👇",
        "place_online": "onlayn",
        "place_room": "offlayn, {room}",
        "place_offline": "offlayn",
        "menu": "Menyu 👇",
        "btn_admin": "📊 Admin panel",
        "admin_denied": "⛔ Bu bo'lim faqat administratorlar uchun.",
        "admin_title": "📊 <b>Admin panel</b> · {period}",
        "admin_users": "👥 <b>Foydalanuvchilar</b>",
        "admin_bot": "🤖 Bot: <b>{total}</b> · yangi <b>+{new}</b>",
        "admin_bot_registered": "ro'yxatdan o'tgan: {count}",
        "admin_bot_guests": "ro'yxatdan o'tmagan: {count}",
        "admin_bot_blocked": "botni bloklagan: {count}",
        "admin_bot_muted": "yangiliklarni o'chirgan: {count}",
        "admin_site": "🌐 Sayt (o'quvchilar): <b>{total}</b> · yangi <b>+{new}</b>",
        "admin_site_telegram": "Telegram ulangan: {count}",
        "admin_site_kids": "SIFAT Kids: {count}",
        "admin_learning": "📚 <b>O'qish</b>",
        "admin_lessons": "tugatilgan darslar: <b>{count}</b>",
        "admin_quizzes": "o'tilgan testlar: <b>{count}</b>",
        "admin_learners": "o'qigan o'quvchilar: <b>{count}</b>",
        "admin_homework": "tekshiruv kutayotgan vazifalar: <b>{count}</b>",
        "admin_sales": "💰 <b>Savdo</b>",
        "admin_chose": "kurs tanladi: <b>{count}</b>",
        "admin_paid": "to'ladi: <b>{count}</b> — {amount}",
        "admin_leads": "arizalar: <b>{count}</b> (AI orqali: {ai})",
        "admin_ai": "AI suhbatlar: <b>{count}</b> · ${cost}",
        "admin_money": "{amount} so'm",
        "admin_problems": "⚠️ <b>Muammolar</b>",
        "admin_no_problems": "✅ Muammo yo'q",
        "admin_updated": "🕒 {time} holatiga",
        "admin_refresh": "🔄 Yangilash",
        "admin_open_site": "🖥 Admin panel (sayt)",
        "admin_broadcast": "📣 Xabar yuborish",
        "period_today": "Bugun",
        "period_yesterday": "Kecha",
        "period_7d": "7 kun",
        "period_30d": "30 kun",
    },
    "ru": {
        "subscribe": (
            "Чтобы пользоваться ботом, подпишитесь на наш канал и нажмите «✅ Я подписался»."
        ),
        "btn_subscribed": "✅ Я подписался",
        "not_subscribed": "Вы ещё не подписались. Вступите в канал и нажмите снова.",
        "welcome": (
            "Здравствуйте{name}! Добро пожаловать в бот Sifat Edu.\n\n"
            "Здесь вы проходите тесты к урокам, смотрите расписание, получаете новости, а на "
            "вопросы отвечает ИИ-консультант.\n\n"
            "Для регистрации нажмите «📱 Отправить телефон» — SMS не нужна."
        ),
        "terms": (
            'Нажимая кнопку, вы принимаете <a href="{offer}">публичную оферту</a> и '
            '<a href="{privacy}">политику конфиденциальности</a>.'
        ),
        "welcome_back": "С возвращением{name}! Выберите раздел в меню.",
        "btn_contact": "📱 Отправить телефон",
        "btn_courses": "📚 Мои курсы",
        "btn_tests": "📝 Тесты",
        "btn_schedule": "📅 Расписание",
        "btn_invite": "🎁 Пригласить друга",
        "btn_ask": "💬 Задать вопрос",
        "btn_settings": "⚙️ Настройки",
        "not_own": "Пожалуйста, отправьте свой номер кнопкой «📱 Отправить телефон».",
        "only_uz": "Пока регистрация доступна только с номерами Узбекистана (+998).",
        "staff_contact": (
            "Этот номер принадлежит сотруднику. Сотрудники подключают Telegram в кабинете на "
            "сайте кнопкой «Подключить Telegram»."
        ),
        "account_blocked": "Этот аккаунт заблокирован. Свяжитесь с поддержкой.",
        "registered": (
            "🎉 Аккаунт создан! Видеоуроки — на сайте: кнопка «🖥 Войти на сайт» открывает его "
            "без пароля."
        ),
        "linked": "✅ Telegram подключён к вашему аккаунту{name}!",
        "need_account": "Сначала зарегистрируйтесь: нажмите «📱 Отправить телефон».",
        "ask": (
            "Напишите вопрос — ответит ИИ-консультант. Спрашивайте о курсах, ценах и о том, какое "
            "направление вам подходит."
        ),
        "help": (
            "/menu — меню\n/tests — тесты\n/schedule — расписание\n/settings — настройки\n\n"
            "Напишите любой вопрос — ответит ИИ-консультант."
        ),
        "courses_title": "📚 <b>Ваши курсы</b>",
        "course_line": "<b>{title}</b> — {percent}% ({done}/{total})\nСледующий урок: {lesson}",
        "course_done": "<b>{title}</b> — пройден ✅",
        "no_courses": (
            "У вас пока нет курсов. Посмотрите курсы на сайте или напишите вопрос — ИИ-консультант "
            "поможет выбрать."
        ),
        "btn_catalog": "📚 Каталог курсов",
        "tests_title": "📝 <b>Тесты</b>",
        "tests_open": "Доступные тесты:",
        "tests_line": "• {lesson} — {course}",
        "tests_empty": (
            "Новых тестов пока нет. Посмотрите следующий урок на сайте — тест к нему появится "
            "здесь."
        ),
        "tests_passed": "Пройдено тестов: {count}",
        "btn_quiz_resume": "▶️ {lesson}",
        "schedule_title": "📅 <b>Ближайшие занятия</b>",
        "schedule_empty": "В ближайшие дни живых занятий нет.",
        "schedule_no_group": "Вы ещё не в группе — расписание появится после добавления в группу.",
        "schedule_line": "<b>{when}</b>\n{course} · {group} · {place}",
        "schedule_topic": "Тема: {topic}",
        "schedule_canceled": "❌ Отменено: {reason}",
        "schedule_join_hint": "Кнопка «Подключиться» появится за 15 минут до начала.",
        "btn_join": "🔗 Подключиться · {time}",
        "invite": (
            "🎁 <b>Приглашайте друзей</b>\n\n"
            "Ваша ссылка (бот):\n{bot}\n\nЧерез сайт:\n{site}\n\n"
            "Вы пригласили: <b>{count}</b>."
        ),
        "invite_rewards": "<b>Награды</b>",
        "invite_lesson": "🪙 Друг завершит первый урок — <b>+{coins} монет</b>",
        "invite_paid": "💳 Друг оплатит курс — <b>{reward}</b>",
        "invite_coins": "+{coins} монет",
        "invite_coupon": "купон {percent}%",
        "invite_and": " и ",
        "invite_discount": "🎉 Другу — <b>скидка {percent}%</b> на первую оплату",
        "btn_share": "📤 Отправить друзьям",
        "share_text": "Изучаю IT в Sifat Edu — присоединяйся!",
        "settings": "⚙️ <b>Настройки</b>\n\nЯзык: {language}\nНовости: {news}",
        "news_on": "включены ✅",
        "news_off": "выключены",
        "btn_language": "🌐 Сменить язык",
        "btn_news_off": "🔕 Выключить новости",
        "btn_news_on": "🔔 Включить новости",
        "btn_site": "🖥 Войти на сайт",
        "news_muted": "Новости выключены. Включить снова: ⚙️ Настройки.",
        "news_enabled": "Новости включены.",
        "quiz_intro": (
            "📝 <b>{title}</b>\n{lesson}\n\n{count} вопросов · для зачёта {percent}%.\n"
            "После каждого ответа видно, верно или нет, а правильные ответы — после сдачи теста."
        ),
        "quiz_resume": "Продолжаем тест: <b>{title}</b>",
        "quiz_missing": "Тест не найден или в нём ещё нет вопросов.",
        "quiz_no_access": "Этот курс вам недоступен.",
        "quiz_locked": "Этот урок пока закрыт: сначала сдайте тест урока «{lesson}».",
        "quiz_offline_locked": "Тест этого урока откроется, когда преподаватель пройдёт урок.",
        "q_head": "<b>{index}/{total}.</b> {text}",
        "q_single_hint": "Выберите один ответ:",
        "q_multiple_hint": "Верных ответов несколько — отметьте их и нажмите «✅ Готово»:",
        "q_text_hint": "✍️ Напишите ответ сообщением.",
        "q_order_hint": "Нажимайте в правильном порядке, начиная с первого:",
        "q_order_chosen": "Порядок: {items}",
        "q_match_hint": "Для каждого пункта слева выберите пару:",
        "q_match_prompt": "«{item}» → ?",
        "btn_done": "✅ Готово",
        "btn_reset": "↩️ Заново",
        "q_right": "✅ Верно",
        "q_wrong": "❌ Неверно",
        "q_your": "Ваш ответ: {answer}",
        "q_pick_one": "Отметьте хотя бы один ответ.",
        "q_stale": "Этот вопрос закрыт — ответьте на последний вопрос.",
        "result_pass": "🎉 <b>Тест сдан!</b>\nРезультат: {score}% ({correct}/{total}) {stars}",
        "result_fail": (
            "😕 Результат: {score}% ({correct}/{total}). Для зачёта нужно {percent}%.\n\n"
            "Пересмотрите видео и попробуйте снова."
        ),
        "review_title": "<b>Работа над ошибками</b>",
        "review_all_right": "Все ответы верные! 👏",
        "review_item": "❌ <b>{index}.</b> {question}\nВы: {yours}\nВерный ответ: {right}",
        "review_note": "💡 {text}",
        "btn_next_lesson": "▶️ К следующему уроку",
        "btn_course": "📚 Вернуться к курсу",
        "btn_retry": "🔁 Ещё раз",
        "btn_video": "🎬 Смотреть видео",
        "btn_open": "Открыть",
        "no_answer": "нет ответа",
        "btn_today": "✅ Задания на сегодня",
        "today_title": "✅ <b>Задания на сегодня</b>",
        "today_lesson": "Посмотрите урок: {title}",
        "today_quiz": "Пройдите тест: {title}",
        "today_review": "Повторите в боте: 5 вопросов",
        "today_homework": "Сдайте домашнее задание: {title}",
        "today_live": "Приходите на урок вовремя: {title}",
        "today_done": "🎉 Всё выполнено! Завтра — новые задания.",
        "today_empty": "Сегодня заданий нет. Задания выдаются каждый день в 09:00.",
        "today_morning": "☀️ Доброе утро! Сегодня три задания — выполните их, и серия продолжится.",
        "btn_today_lesson": "▶️ Открыть урок",
        "btn_today_quiz": "📝 Начать тест",
        "btn_today_review": "🔁 Повторить",
        "btn_today_homework": "📎 Открыть задание",
        "btn_today_live": "📅 Расписание",
        "review_intro": (
            "🔁 <b>Повторение</b>: {count} вопросов из пройденных тестов. После каждого ответа — "
            "верно или нет."
        ),
        "review_empty": "Для повторения пока нет пройденных тестов — сначала пройдите тест урока.",
        "review_done": "🔁 Повторение завершено: верно {correct}/{total}.",
        "winners_title": "🏆 <b>Самые активные ученики недели</b>",
        "winners_footer": "Поздравляем! Новая неделя — новые возможности 💪",
        "tests_exam": "🏆 <b>Ежемесячный экзамен открыт</b>: {course}",
        "btn_exam": "🏆 Экзамен: {course}",
        "exam_intro": (
            "🏆 <b>Ежемесячный экзамен</b> — {course}\n\n{count} вопросов · {minutes} минут · "
            "одна попытка. Время пойдёт после «Начать».\nВерно ли вы ответили — покажем после "
            "закрытия экзамена. Практические задания — на сайте."
        ),
        "btn_exam_start": "▶️ Начать",
        "btn_exam_tasks": "🖥 Практические задания",
        "exam_time_left": "⏳ Осталось {minutes} мин",
        "exam_saved": "✔️ Ответ сохранён",
        "exam_done": (
            "✅ <b>Тест завершён</b>: {score}%.\nПравильные ответы покажем после закрытия "
            "экзамена. Практические задания сдайте на сайте."
        ),
        "exam_closed": "Экзамен сейчас закрыт.",
        "exam_already": "Вы уже сдали тест экзамена: {score}%. Практические задания — на сайте.",
        "only_text": "Пока я понимаю только текстовые сообщения — напишите вопрос.",
        "site_hint": "Видеоуроки и кабинет — на сайте 👇",
        "place_online": "онлайн",
        "place_room": "офлайн, {room}",
        "place_offline": "офлайн",
        "menu": "Меню 👇",
        "btn_admin": "📊 Админ-панель",
        "admin_denied": "⛔ Этот раздел только для администраторов.",
        "admin_title": "📊 <b>Админ-панель</b> · {period}",
        "admin_users": "👥 <b>Пользователи</b>",
        "admin_bot": "🤖 Бот: <b>{total}</b> · новых <b>+{new}</b>",
        "admin_bot_registered": "зарегистрированы: {count}",
        "admin_bot_guests": "не зарегистрированы: {count}",
        "admin_bot_blocked": "заблокировали бота: {count}",
        "admin_bot_muted": "отключили новости: {count}",
        "admin_site": "🌐 Сайт (ученики): <b>{total}</b> · новых <b>+{new}</b>",
        "admin_site_telegram": "Telegram подключён: {count}",
        "admin_site_kids": "SIFAT Kids: {count}",
        "admin_learning": "📚 <b>Обучение</b>",
        "admin_lessons": "завершено уроков: <b>{count}</b>",
        "admin_quizzes": "пройдено тестов: <b>{count}</b>",
        "admin_learners": "учились: <b>{count}</b>",
        "admin_homework": "заданий ждут проверки: <b>{count}</b>",
        "admin_sales": "💰 <b>Продажи</b>",
        "admin_chose": "выбрали курс: <b>{count}</b>",
        "admin_paid": "оплатили: <b>{count}</b> — {amount}",
        "admin_leads": "заявки: <b>{count}</b> (через ИИ: {ai})",
        "admin_ai": "диалоги с ИИ: <b>{count}</b> · ${cost}",
        "admin_money": "{amount} сум",
        "admin_problems": "⚠️ <b>Проблемы</b>",
        "admin_no_problems": "✅ Проблем нет",
        "admin_updated": "🕒 Данные на {time}",
        "admin_refresh": "🔄 Обновить",
        "admin_open_site": "🖥 Админ-панель (сайт)",
        "admin_broadcast": "📣 Отправить сообщение",
        "period_today": "Сегодня",
        "period_yesterday": "Вчера",
        "period_7d": "7 дней",
        "period_30d": "30 дней",
    },
    "en": {
        "subscribe": "To use the bot, join our channel and then tap «✅ I have joined».",
        "btn_subscribed": "✅ I have joined",
        "not_subscribed": "You have not joined yet. Join the channel and tap again.",
        "welcome": (
            "Hello{name}! Welcome to the Sifat Edu bot.\n\n"
            "Here you take lesson quizzes, check your schedule and get news, and the AI advisor "
            "answers your questions.\n\n"
            "To sign up, tap «📱 Share phone» — no SMS needed."
        ),
        "terms": (
            'By tapping the button you accept the <a href="{offer}">public offer</a> and the '
            '<a href="{privacy}">privacy policy</a>.'
        ),
        "welcome_back": "Welcome back{name}! Pick a section from the menu.",
        "btn_contact": "📱 Share phone",
        "btn_courses": "📚 My courses",
        "btn_tests": "📝 Quizzes",
        "btn_schedule": "📅 Schedule",
        "btn_invite": "🎁 Invite a friend",
        "btn_ask": "💬 Ask a question",
        "btn_settings": "⚙️ Settings",
        "not_own": "Please share your own number with the «📱 Share phone» button.",
        "only_uz": "For now only Uzbekistan numbers (+998) can sign up.",
        "staff_contact": (
            "This number belongs to a staff account. Staff connect Telegram from the website "
            "dashboard with «Connect Telegram»."
        ),
        "account_blocked": "This account is blocked. Please contact support.",
        "registered": (
            "🎉 Your account is ready! Video lessons are on the website: «🖥 Open the website» "
            "signs you in without a password."
        ),
        "linked": "✅ Telegram is connected to your account{name}!",
        "need_account": "Please sign up first: tap «📱 Share phone».",
        "ask": (
            "Type your question — the AI advisor will answer. Ask about courses, prices and which "
            "direction suits you."
        ),
        "help": (
            "/menu — menu\n/tests — quizzes\n/schedule — schedule\n/settings — settings\n\n"
            "Type any question — the AI advisor will answer."
        ),
        "courses_title": "📚 <b>Your courses</b>",
        "course_line": "<b>{title}</b> — {percent}% ({done}/{total})\nNext lesson: {lesson}",
        "course_done": "<b>{title}</b> — completed ✅",
        "no_courses": (
            "You have no courses yet. Browse them on the website or ask a question — the AI "
            "advisor will help you choose."
        ),
        "btn_catalog": "📚 Course catalog",
        "tests_title": "📝 <b>Quizzes</b>",
        "tests_open": "Quizzes you can take:",
        "tests_line": "• {lesson} — {course}",
        "tests_empty": (
            "No new quizzes yet. Watch the next lesson on the website — its quiz will appear here."
        ),
        "tests_passed": "Quizzes passed: {count}",
        "btn_quiz_resume": "▶️ {lesson}",
        "schedule_title": "📅 <b>Upcoming classes</b>",
        "schedule_empty": "No live classes in the coming days.",
        "schedule_no_group": "You are not in a group yet — the schedule appears once you join one.",
        "schedule_line": "<b>{when}</b>\n{course} · {group} · {place}",
        "schedule_topic": "Topic: {topic}",
        "schedule_canceled": "❌ Canceled: {reason}",
        "schedule_join_hint": "The «Join» button appears 15 minutes before the class starts.",
        "btn_join": "🔗 Join · {time}",
        "invite": (
            "🎁 <b>Invite your friends</b>\n\n"
            "Your link (bot):\n{bot}\n\nVia the website:\n{site}\n\n"
            "Friends invited: <b>{count}</b>."
        ),
        "invite_rewards": "<b>Rewards</b>",
        "invite_lesson": "🪙 Your friend finishes the first lesson — <b>+{coins} coins</b>",
        "invite_paid": "💳 Your friend pays — <b>{reward}</b>",
        "invite_coins": "+{coins} coins",
        "invite_coupon": "a {percent}% coupon",
        "invite_and": " and ",
        "invite_discount": "🎉 Your friend gets <b>{percent}% off</b> the first payment",
        "btn_share": "📤 Send to friends",
        "share_text": "I am learning IT at Sifat Edu — join me!",
        "settings": "⚙️ <b>Settings</b>\n\nLanguage: {language}\nNews: {news}",
        "news_on": "on ✅",
        "news_off": "off",
        "btn_language": "🌐 Change language",
        "btn_news_off": "🔕 Turn off news",
        "btn_news_on": "🔔 Turn on news",
        "btn_site": "🖥 Open the website",
        "news_muted": "News is off. Turn it back on in ⚙️ Settings.",
        "news_enabled": "News is on.",
        "quiz_intro": (
            "📝 <b>{title}</b>\n{lesson}\n\n{count} questions · {percent}% to pass.\n"
            "After each answer you see whether it is right; correct answers are shown once you "
            "pass."
        ),
        "quiz_resume": "Continuing the quiz: <b>{title}</b>",
        "quiz_missing": "The quiz was not found or has no questions yet.",
        "quiz_no_access": "This course is not open to you.",
        "quiz_locked": "This lesson is still locked: pass the quiz of «{lesson}» first.",
        "quiz_offline_locked": "This quiz opens once your teacher covers the lesson.",
        "q_head": "<b>{index}/{total}.</b> {text}",
        "q_single_hint": "Pick one answer:",
        "q_multiple_hint": "Several answers are right — tick them and tap «✅ Done»:",
        "q_text_hint": "✍️ Type your answer as a message.",
        "q_order_hint": "Tap in the right order, starting with the first:",
        "q_order_chosen": "Order: {items}",
        "q_match_hint": "Pick a pair for each item on the left:",
        "q_match_prompt": "«{item}» → ?",
        "btn_done": "✅ Done",
        "btn_reset": "↩️ Start over",
        "q_right": "✅ Right",
        "q_wrong": "❌ Wrong",
        "q_your": "Your answer: {answer}",
        "q_pick_one": "Tick at least one answer.",
        "q_stale": "This question is closed — answer the latest one.",
        "result_pass": "🎉 <b>Quiz passed!</b>\nScore: {score}% ({correct}/{total}) {stars}",
        "result_fail": (
            "😕 Score: {score}% ({correct}/{total}). You need {percent}% to pass.\n\n"
            "Rewatch the video and try again."
        ),
        "review_title": "<b>Your mistakes</b>",
        "review_all_right": "All answers are right! 👏",
        "review_item": "❌ <b>{index}.</b> {question}\nYou: {yours}\nRight answer: {right}",
        "review_note": "💡 {text}",
        "btn_next_lesson": "▶️ Next lesson",
        "btn_course": "📚 Back to the course",
        "btn_retry": "🔁 Try again",
        "btn_video": "🎬 Watch the video",
        "btn_open": "Open",
        "no_answer": "no answer",
        "btn_today": "✅ Today's tasks",
        "today_title": "✅ <b>Today's tasks</b>",
        "today_lesson": "Watch the lesson: {title}",
        "today_quiz": "Pass the quiz: {title}",
        "today_review": "Review in the bot: 5 questions",
        "today_homework": "Submit the homework: {title}",
        "today_live": "Come to class on time: {title}",
        "today_done": "🎉 All done! New tasks tomorrow.",
        "today_empty": "No tasks today. Tasks are given every day at 09:00.",
        "today_morning": "☀️ Good morning! Three tasks today — complete them to keep your streak.",
        "btn_today_lesson": "▶️ Open the lesson",
        "btn_today_quiz": "📝 Start the quiz",
        "btn_today_review": "🔁 Review",
        "btn_today_homework": "📎 Open the homework",
        "btn_today_live": "📅 Schedule",
        "review_intro": (
            "🔁 <b>Review</b>: {count} questions from quizzes you passed. After each answer — "
            "right or wrong."
        ),
        "review_empty": "Nothing to review yet — pass a lesson quiz first.",
        "review_done": "🔁 Review finished: {correct}/{total} correct.",
        "winners_title": "🏆 <b>Most active students of the week</b>",
        "winners_footer": "Congratulations! A new week — a new chance 💪",
        "tests_exam": "🏆 <b>Monthly exam is open</b>: {course}",
        "btn_exam": "🏆 Monthly exam: {course}",
        "exam_intro": (
            "🏆 <b>Monthly exam</b> — {course}\n\n{count} questions · {minutes} minutes · one "
            "attempt. The timer starts when you tap «Start».\nWhether your answers were right is "
            "shown after the exam closes. Practical tasks are on the website."
        ),
        "btn_exam_start": "▶️ Start",
        "btn_exam_tasks": "🖥 Practical tasks",
        "exam_time_left": "⏳ {minutes} min left",
        "exam_saved": "✔️ Answer saved",
        "exam_done": (
            "✅ <b>Quiz part finished</b>: {score}%.\nCorrect answers are shown after the exam "
            "closes. Submit the practical tasks on the website."
        ),
        "exam_closed": "The exam is not open now.",
        "exam_already": (
            "You have taken the exam quiz: {score}%. Practical tasks are on the website."
        ),
        "only_text": "For now I understand only text messages — please type your question.",
        "site_hint": "Video lessons and your dashboard are on the website 👇",
        "place_online": "online",
        "place_room": "in class, {room}",
        "place_offline": "in class",
        "menu": "Menu 👇",
        "btn_admin": "📊 Admin panel",
        "admin_denied": "⛔ This section is for administrators only.",
        "admin_title": "📊 <b>Admin panel</b> · {period}",
        "admin_users": "👥 <b>Users</b>",
        "admin_bot": "🤖 Bot: <b>{total}</b> · new <b>+{new}</b>",
        "admin_bot_registered": "signed up: {count}",
        "admin_bot_guests": "not signed up: {count}",
        "admin_bot_blocked": "blocked the bot: {count}",
        "admin_bot_muted": "news turned off: {count}",
        "admin_site": "🌐 Website (students): <b>{total}</b> · new <b>+{new}</b>",
        "admin_site_telegram": "Telegram connected: {count}",
        "admin_site_kids": "SIFAT Kids: {count}",
        "admin_learning": "📚 <b>Learning</b>",
        "admin_lessons": "lessons completed: <b>{count}</b>",
        "admin_quizzes": "quizzes passed: <b>{count}</b>",
        "admin_learners": "students who studied: <b>{count}</b>",
        "admin_homework": "homework awaiting review: <b>{count}</b>",
        "admin_sales": "💰 <b>Sales</b>",
        "admin_chose": "chose a course: <b>{count}</b>",
        "admin_paid": "paid: <b>{count}</b> — {amount}",
        "admin_leads": "leads: <b>{count}</b> (via AI: {ai})",
        "admin_ai": "AI chats: <b>{count}</b> · ${cost}",
        "admin_money": "{amount} UZS",
        "admin_problems": "⚠️ <b>Problems</b>",
        "admin_no_problems": "✅ No problems",
        "admin_updated": "🕒 As of {time}",
        "admin_refresh": "🔄 Refresh",
        "admin_open_site": "🖥 Admin panel (website)",
        "admin_broadcast": "📣 Send a message",
        "period_today": "Today",
        "period_yesterday": "Yesterday",
        "period_7d": "7 days",
        "period_30d": "30 days",
    },
}

# Menyu tugmalari: foydalanuvchi qaysi tilda bossa ham tanib olinadi.
MENU_ACTIONS = ("today", "courses", "tests", "schedule", "invite", "ask", "settings", "admin")
MENU_BY_LABEL = {
    TEXTS[locale][f"btn_{action}"]: action for locale in TEXTS for action in MENU_ACTIONS
}


def language(value: str | None) -> str:
    code = (value or "")[:2].lower()
    return code if code in TEXTS else "uz"


def t(locale: str | None, key: str, **params: object) -> str:
    template = TEXTS[language(locale)].get(key) or TEXTS["uz"][key]
    return template.format(**params) if params else template
