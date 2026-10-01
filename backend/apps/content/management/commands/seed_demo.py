"""Landing'ni ko'rib chiqish uchun namunaviy ma'lumotlar (3 tilda).

Faqat bo'sh jadvallarni to'ldiradi: admin'da kiritilgan ma'lumotlarga tegmaydi.
Kurslar haqiqiy, ammo narx, davomiylik va dastur taxminiy — admin paneldan aniqlanadi.
Ustozlar bu yerda yaratilmaydi: haqiqiy ismlar admin paneldan kiritiladi.
"""

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import Category, Course, Lesson, Module
from apps.content.models import Advantage, Concern, FAQItem, HowStep, LegalPage, SiteSettings

Tr = tuple[str, str, str]  # (uz, ru, en)


def tr(field: str, values: Tr) -> dict[str, str]:
    return {
        f"{field}_{code}": value for code, value in zip(("uz", "ru", "en"), values, strict=True)
    }


SITE = {
    "hero_title": (
        "Kelajagingizni *kod* bilan yozing",
        "Напишите своё будущее *кодом*",
        "Write your future in *code*",
    ),
    "hero_subtitle": (
        "IT kasbini noldan o'rganing: video darslar, amaliy topshiriqlar va tajribali ustozlar. "
        "O'zbek, rus yoki ingliz tilida — o'zingizga qulay vaqtda.",
        "Освойте IT-профессию с нуля: видеоуроки, практические задания и опытные "
        "преподаватели. На узбекском, русском или английском — в удобное время.",
        "Learn an IT profession from scratch: video lessons, hands-on assignments and "
        "experienced mentors. In Uzbek, Russian or English — at your own pace.",
    ),
    "about_text": (
        "Biz — sohada ishlayotgan dasturchi va dizaynerlarmiz. IT'ni murakkab atamalarsiz, "
        "tushunarli tilda o'rgatamiz: har bir mavzu amaliyot bilan mustahkamlanadi. "
        "Maqsadimiz — sizga shunchaki kurs emas, yangi kasb berish.",
        "Мы — разработчики и дизайнеры, которые работают в индустрии. Объясняем IT простым "
        "языком, без сложных терминов, и закрепляем каждую тему практикой. Наша цель — дать "
        "вам не просто курс, а новую профессию.",
        "We are developers and designers who work in the industry. We teach IT in plain "
        "language, without jargon, and back every topic with practice. Our goal is to give "
        "you a new profession, not just a course.",
    ),
    "address": ("Toshkent shahri", "г. Ташкент", "Tashkent"),
    "working_hours": ("Har kuni 09:00–21:00", "Ежедневно 09:00–21:00", "Daily 09:00–21:00"),
}

CONCERNS: list[tuple[Tr, Tr]] = [
    (
        ("Qayerdan boshlashni bilmayman", "Не знаю, с чего начать", "I don't know where to start"),
        (
            "Bepul maslahatda maqsadingizni aniqlaymiz va sizga mos yo'nalishni birga tanlaymiz.",
            "На бесплатной консультации разберём вашу цель и вместе выберем направление.",
            "In a free consultation we'll clarify your goal and pick the right track together.",
        ),
    ),
    (
        (
            "YouTube'dagi darslar tarqoq, oxiriga yetkaza olmayman",
            "Уроки на YouTube разрозненные, никак не доведу до конца",
            "YouTube tutorials are scattered and I never finish",
        ),
        (
            "Har bir kurs — boshidan oxirigacha tartiblangan video darslar va amaliy topshiriqlar.",
            "Каждый курс — выстроенные от начала до конца видеоуроки и практика.",
            "Each course is a structured path of video lessons and hands-on assignments.",
        ),
    ),
    (
        ("Ingliz tilini yaxshi bilmayman", "Плохо знаю английский", "My English isn't great"),
        (
            "Kurslar o'zbek, rus va ingliz tillarida — o'zingizga qulayini tanlang.",
            "Курсы на узбекском, русском и английском — выбирайте удобный язык.",
            "Courses come in Uzbek, Russian and English — pick the one that suits you.",
        ),
    ),
    (
        (
            "Vaqtim kam: ish, o'qish, oila",
            "Мало времени: работа, учёба, семья",
            "I'm short on time: work, studies, family",
        ),
        (
            "Istalgan vaqtda o'qing: progress saqlanadi, to'xtagan joyingizdan davom etasiz.",
            "Учитесь когда удобно: прогресс сохраняется, вы продолжаете с того же места.",
            "Study whenever you can: progress is saved and you pick up where you left off.",
        ),
    ),
    (
        ("Internetim sekin", "У меня медленный интернет", "My internet is slow"),
        (
            "Video sifati internet tezligingizga moslashadi — dars uzilmaydi.",
            "Качество видео подстраивается под скорость интернета — урок не прерывается.",
            "Video quality adapts to your connection, so the lesson keeps playing.",
        ),
    ),
    (
        (
            "Menga qiyin bo'lib qolsa-chi?",
            "А если будет слишком сложно?",
            "What if it's too hard for me?",
        ),
        (
            "Boshlang'ich kurslar noldan boshlanadi va hammasini bosqichma-bosqich tushuntiradi.",
            "Курсы начального уровня стартуют с нуля и объясняют всё шаг за шагом.",
            "Beginner courses start from zero and explain everything step by step.",
        ),
    ),
]

ADVANTAGES: list[tuple[str, Tr, Tr]] = [
    (
        "video",
        ("Istalgan vaqtda video darslar", "Видеоуроки в любое время", "Video lessons anytime"),
        (
            "Darslarni o'zingizga qulay vaqtda ko'ring va to'xtagan joyingizdan davom ettiring.",
            "Смотрите уроки в удобное время и продолжайте с того места, где остановились.",
            "Watch lessons whenever it suits you and continue right where you left off.",
        ),
    ),
    (
        "code",
        ("Amaliyotga yo'naltirilgan dastur", "Упор на практику", "Practice-first curriculum"),
        (
            "Har bir modulda real loyihaga yaqin topshiriqlar — portfolio uchun tayyor ishlar.",
            "В каждом модуле — задания, близкие к реальным проектам, и работы для портфолио.",
            "Every module has real-world assignments that become part of your portfolio.",
        ),
    ),
    (
        "users",
        ("Tajribali ustozlar", "Опытные преподаватели", "Experienced mentors"),
        (
            "Kurslarni sohada ishlayotgan mutaxassislar tayyorlaydi.",
            "Курсы готовят специалисты, которые работают в индустрии.",
            "Courses are built by practitioners who work in the industry.",
        ),
    ),
    (
        "languages",
        ("Uch tilda", "На трёх языках", "Three languages"),
        (
            "Interfeys va kurslar o'zbek, rus va ingliz tillarida.",
            "Интерфейс и курсы на узбекском, русском и английском.",
            "The platform and courses are available in Uzbek, Russian and English.",
        ),
    ),
    (
        "wifi",
        ("Sekin internetda ham", "Даже при медленном интернете", "Works on slow internet"),
        (
            "Video sifati internet tezligingizga moslashadi — darslar uzilmaydi.",
            "Качество видео подстраивается под скорость интернета — уроки не прерываются.",
            "Video quality adapts to your connection, so lessons keep playing.",
        ),
    ),
    (
        "infinity",
        ("Umrbod kirish", "Бессрочный доступ", "Lifetime access"),
        (
            "Bir marta to'lang — kurs materiallari doim siz bilan.",
            "Оплатите один раз — материалы курса останутся с вами навсегда.",
            "Pay once and keep access to the course materials for good.",
        ),
    ),
]

STEPS: list[tuple[Tr, Tr]] = [
    (
        ("Ariza qoldiring", "Оставьте заявку", "Leave a request"),
        (
            "Bepul maslahat oling — sizga mos kursni birga tanlaymiz.",
            "Получите бесплатную консультацию — вместе подберём подходящий курс.",
            "Get a free consultation and we'll pick the right course together.",
        ),
    ),
    (
        ("Kursni tanlang", "Выберите курс", "Choose a course"),
        (
            "Dastur, ustoz va narx bilan tanishing, Click orqali xavfsiz to'lang.",
            "Изучите программу, преподавателя и цену, безопасно оплатите через Click.",
            "Review the syllabus, mentor and price, then pay securely with Click.",
        ),
    ),
    (
        ("O'qing va mashq qiling", "Учитесь и практикуйтесь", "Learn and practice"),
        (
            "Video darslarni ko'ring, topshiriqlarni bajaring — progressingiz saqlanib boradi.",
            "Смотрите уроки, выполняйте задания — ваш прогресс сохраняется.",
            "Watch the lessons and do the assignments while your progress is saved.",
        ),
    ),
    (
        ("Natijaga erishing", "Получите результат", "Reach your goal"),
        (
            "Amaliy ko'nikmalar va portfolio bilan yangi kasbga qadam qo'ying.",
            "Сделайте шаг в новую профессию с практическими навыками и портфолио.",
            "Step into a new profession with practical skills and a portfolio.",
        ),
    ),
]

FAQ: list[tuple[Tr, Tr]] = [
    (
        (
            "Dasturlashni umuman bilmasam ham o'qiy olamanmi?",
            "Смогу ли я учиться, если совсем не знаю программирования?",
            "Can I join if I have never programmed before?",
        ),
        (
            "Ha. Boshlang'ich kurslar noldan boshlanadi va hamma narsani bosqichma-bosqich "
            "tushuntiradi.",
            "Да. Курсы начального уровня начинаются с нуля и объясняют всё пошагово.",
            "Yes. Beginner courses start from zero and explain everything step by step.",
        ),
    ),
    (
        (
            "To'lovni qanday amalga oshiraman?",
            "Как оплатить обучение?",
            "How do I pay?",
        ),
        (
            "Kurs sahifasidan Click orqali to'laysiz. To'lovdan so'ng kurs avtomatik ochiladi.",
            "Оплата через Click на странице курса. После оплаты курс открывается автоматически.",
            "Pay with Click on the course page. The course unlocks automatically after payment.",
        ),
    ),
    (
        (
            "Kursga kirish qancha muddat amal qiladi?",
            "Как долго действует доступ к курсу?",
            "How long do I keep access to a course?",
        ),
        (
            "Bir marta sotib olingan kursga umrbod kirish beriladi.",
            "Купленный курс остаётся доступен бессрочно.",
            "A purchased course stays available for life.",
        ),
    ),
    (
        (
            "Pulni qaytarib olsa bo'ladimi?",
            "Можно ли вернуть деньги?",
            "Can I get a refund?",
        ),
        (
            "Ha, pulni qaytarish qoidalarida belgilangan shartlar asosida. Batafsil — "
            "«Pulni qaytarish qoidalari» sahifasida.",
            "Да, на условиях, указанных в правилах возврата. Подробнее — на странице "
            "«Правила возврата».",
            "Yes, under the conditions set out in our refund policy page.",
        ),
    ),
    (
        (
            "Darslarni telefondan ko'rsa bo'ladimi?",
            "Можно ли смотреть уроки с телефона?",
            "Can I watch lessons on my phone?",
        ),
        (
            "Ha, platforma telefon, planshet va kompyuterda ishlaydi.",
            "Да, платформа работает на телефоне, планшете и компьютере.",
            "Yes, the platform works on phones, tablets and computers.",
        ),
    ),
    (
        (
            "Internetim sekin bo'lsa-chi?",
            "А если у меня медленный интернет?",
            "What if my internet is slow?",
        ),
        (
            "Video sifati internet tezligiga qarab avtomatik moslashadi, shuning uchun darslar "
            "uzilmaydi.",
            "Качество видео автоматически подстраивается под скорость, поэтому уроки не "
            "прерываются.",
            "Video quality adjusts automatically to your connection, so lessons don't stall.",
        ),
    ),
]

CATEGORIES: list[tuple[str, Tr]] = [
    ("bolalar", ("Bolalar uchun", "Для детей", "For kids")),
    ("savodxonlik", ("Kompyuter savodxonligi", "Компьютерная грамотность", "Computer literacy")),
    ("dasturlash", ("Dasturlash", "Программирование", "Programming")),
    ("praktikum", ("Praktikum", "Практикум", "Practicum")),
    ("tillar", ("Til kurslari", "Языковые курсы", "Language courses")),
]

# Kurslar haqiqiy. Narx, davomiylik va dastur taxminiy: admin paneldan aniqlanadi.
COURSES: list[dict[str, Any]] = [
    {
        "slug": "sifat-kids",
        "category": "bolalar",
        "audience": Course.Audience.KIDS,
        "age": (7, 11),
        "level": Course.Level.BEGINNER,
        "price_online": 1_200_000,
        "price_offline_monthly": 500_000,
        "duration_hours": 64,
        "icon": Course.Icon.BLOCKS,
        "featured": True,
        "title": (
            "SIFAT Kids: kompyuter (7–11 yosh)",
            "SIFAT Kids: компьютер (7–11 лет)",
            "SIFAT Kids: computers (ages 7–11)",
        ),
        "short_description": (
            "Bolajonlar kompyuterni noldan professional darajada o'rganadi: xavfsiz internet, "
            "hujjat va grafika, so'ng birinchi kod.",
            "Дети осваивают компьютер с нуля до профессионального уровня: безопасный интернет, "
            "документы и графика, затем первый код.",
            "Children learn the computer from zero to a professional level: safe internet, "
            "documents and graphics, then their first code.",
        ),
    },
    {
        "slug": "kompyuter-savodxonligi",
        "category": "savodxonlik",
        "level": Course.Level.BEGINNER,
        "price_online": 700_000,
        "price_offline_monthly": 400_000,
        "duration_hours": 40,
        "icon": Course.Icon.MONITOR,
        "featured": True,
        "title": ("Kompyuter savodxonligi", "Компьютерная грамотность", "Computer literacy"),
        "short_description": (
            "Kompyuter, internet va ofis dasturlarini noldan o'rganing — ishda ham, kundalik "
            "hayotda ham ishonch bilan foydalanasiz.",
            "Освойте компьютер, интернет и офисные программы с нуля — уверенно и на работе, "
            "и в повседневной жизни.",
            "Learn computers, the internet and office software from scratch — with confidence "
            "at work and in everyday life.",
        ),
    },
    {
        "slug": "frontend",
        "category": "dasturlash",
        "level": Course.Level.BEGINNER,
        "price_online": 1_800_000,
        "price_offline_monthly": 700_000,
        "duration_hours": 80,
        "icon": Course.Icon.CODE,
        "featured": True,
        "title": ("Frontend dasturlash", "Frontend-разработка", "Frontend development"),
        "short_description": (
            "HTML, CSS, JavaScript va React: noldan zamonaviy veb-interfeyslar va portfolio "
            "bilan birinchi ish o'rniga.",
            "HTML, CSS, JavaScript и React: с нуля до современных веб-интерфейсов и первой "
            "работы с портфолио.",
            "HTML, CSS, JavaScript and React: from scratch to modern web interfaces and a "
            "first job with a portfolio.",
        ),
    },
    {
        "slug": "backend",
        "category": "dasturlash",
        "level": Course.Level.INTERMEDIATE,
        "price_online": 1_800_000,
        "price_offline_monthly": 700_000,
        "duration_hours": 88,
        "icon": Course.Icon.SERVER,
        "featured": True,
        "title": ("Backend dasturlash", "Backend-разработка", "Backend development"),
        "short_description": (
            "Python, ma'lumotlar bazasi va API: saytning ko'rinmas, lekin eng muhim qismini "
            "yozishni o'rganing.",
            "Python, базы данных и API: научитесь писать невидимую, но самую важную часть "
            "продукта.",
            "Python, databases and APIs: learn to build the invisible but most important part "
            "of a product.",
        ),
    },
    {
        "slug": "suniy-intellekt",
        "category": "dasturlash",
        "level": Course.Level.ADVANCED,
        "price_online": 2_200_000,
        "price_offline_monthly": 800_000,
        "duration_hours": 72,
        "icon": Course.Icon.BRAIN,
        "title": ("Sun'iy intellekt", "Искусственный интеллект", "Artificial intelligence"),
        "short_description": (
            "Ma'lumot bilan ishlash, modellar va tayyor AI xizmatlari: g'oyadan ishlaydigan "
            "mahsulotgacha.",
            "Работа с данными, модели и готовые AI-сервисы: от идеи до работающего продукта.",
            "Working with data, models and ready-made AI services: from idea to a working product.",
        ),
    },
    {
        "slug": "praktikum-frontend",
        "category": "praktikum",
        "level": Course.Level.INTERMEDIATE,
        "price_online": 1_400_000,
        "price_offline_monthly": 600_000,
        "duration_hours": 60,
        "icon": Course.Icon.TERMINAL,
        "title": ("Praktikum: Frontend", "Практикум: Frontend", "Practicum: Frontend"),
        "short_description": (
            "Nazariya emas — amaliyot: haqiqiy loyihalar, kod ko'rigi va jamoada ishlash tartibi.",
            "Не теория, а практика: реальные проекты, код-ревью и работа в команде.",
            "Not theory but practice: real projects, code review and working in a team.",
        ),
    },
    {
        "slug": "praktikum-backend",
        "category": "praktikum",
        "level": Course.Level.INTERMEDIATE,
        "price_online": 1_400_000,
        "price_offline_monthly": 600_000,
        "duration_hours": 60,
        "icon": Course.Icon.DATABASE,
        "title": ("Praktikum: Backend", "Практикум: Backend", "Practicum: Backend"),
        "short_description": (
            "Servis yozish, test, deploy va monitoring — ish joyidagi kunlik vazifalar bilan "
            "bir xil tartibda.",
            "Написание сервиса, тесты, деплой и мониторинг — в том же порядке, что и на работе.",
            "Building a service, tests, deployment and monitoring — in the same order as on "
            "the job.",
        ),
    },
    {
        "slug": "ingliz-tili",
        "category": "tillar",
        "level": Course.Level.BEGINNER,
        "price_online": 900_000,
        "price_offline_monthly": 450_000,
        "duration_hours": 96,
        "icon": Course.Icon.LANGUAGES,
        "video_language": "uz",
        "title": ("Ingliz tili", "Английский язык", "English language"),
        "short_description": (
            "Gapirishdan boshlaymiz: kundalik muloqot, ish suhbati va IT uchun kerakli ingliz "
            "tili.",
            "Начинаем с речи: повседневное общение, интервью и английский для IT.",
            "Speaking first: everyday conversation, interviews and the English you need in IT.",
        ),
    },
]

# Kurs dasturi: (modul, [darslar]). Har bir dars ~20 daqiqa; birinchi dars bepul.
PROGRAM: dict[str, list[tuple[Tr, list[Tr]]]] = {
    "sifat-kids": [
        (
            (
                "Kompyuter bilan do'stlashamiz",
                "Дружим с компьютером",
                "Making friends with the computer",
            ),
            [
                ("Sichqoncha va klaviatura", "Мышка и клавиатура", "Mouse and keyboard"),
                ("Fayllar va papkalar", "Файлы и папки", "Files and folders"),
                ("Xavfsiz internet", "Безопасный интернет", "Staying safe online"),
            ],
        ),
        (
            ("Rasm va matn", "Рисунок и текст", "Drawing and text"),
            [
                ("Kompyuterda rasm chizamiz", "Рисуем на компьютере", "Drawing on the computer"),
                ("Birinchi hujjat", "Первый документ", "Your first document"),
                ("Taqdimot yasaymiz", "Делаем презентацию", "Making a presentation"),
            ],
        ),
        (
            ("Birinchi kod: Scratch", "Первый код: Scratch", "First code: Scratch"),
            [
                ("Buyruqlar va algoritm", "Команды и алгоритм", "Commands and algorithms"),
                ("Takrorlash va shartlar", "Циклы и условия", "Loops and conditions"),
                ("O'z o'yinimiz", "Своя игра", "Your own game"),
                ("Multfilm yasaymiz", "Делаем мультфильм", "Making a cartoon"),
            ],
        ),
        (
            ("Yakuniy loyiha", "Итоговый проект", "Final project"),
            [
                ("Loyiha g'oyasi", "Идея проекта", "The project idea"),
                ("Loyihani yig'amiz", "Собираем проект", "Building the project"),
                ("Ota-onalarga taqdimot", "Презентация для родителей", "Presenting to parents"),
            ],
        ),
    ],
    "kompyuter-savodxonligi": [
        (
            (
                "Kompyuter va operatsion tizim",
                "Компьютер и операционная система",
                "The computer and its operating system",
            ),
            [
                ("Kompyuter qanday ishlaydi", "Как работает компьютер", "How a computer works"),
                ("Ish stoli va sozlamalar", "Рабочий стол и настройки", "Desktop and settings"),
                ("Fayllar va zaxira nusxa", "Файлы и резервные копии", "Files and backups"),
            ],
        ),
        (
            ("Internet va xavfsizlik", "Интернет и безопасность", "Internet and safety"),
            [
                ("Brauzer va qidiruv", "Браузер и поиск", "Browsers and search"),
                ("Elektron pochta", "Электронная почта", "Email"),
                ("Parollar va firibgarlik", "Пароли и мошенничество", "Passwords and scams"),
            ],
        ),
        (
            ("Ofis dasturlari", "Офисные программы", "Office software"),
            [
                ("Word: hujjat tayyorlash", "Word: готовим документ", "Word: writing documents"),
                ("Excel: jadval va hisob", "Excel: таблицы и расчёты", "Excel: sheets and sums"),
                ("Taqdimot tayyorlash", "Готовим презентацию", "Building a presentation"),
            ],
        ),
        (
            ("Onlayn xizmatlar", "Онлайн-сервисы", "Online services"),
            [
                ("Karta va to'lovlar", "Карта и платежи", "Cards and payments"),
                (
                    "Davlat xizmatlari va hujjatlar",
                    "Госуслуги и документы",
                    "Government services and documents",
                ),
                (
                    "Telefon va kompyuter birga",
                    "Телефон и компьютер вместе",
                    "Phone and computer together",
                ),
            ],
        ),
    ],
    "frontend": [
        (
            ("HTML: sahifaning skeleti", "HTML: скелет страницы", "HTML: the page skeleton"),
            [
                ("Birinchi veb-sahifa", "Первая веб-страница", "Your first web page"),
                (
                    "Matn, rasm va havolalar",
                    "Текст, изображения и ссылки",
                    "Text, images and links",
                ),
                ("Ro'yxatlar va jadvallar", "Списки и таблицы", "Lists and tables"),
                ("Formalar", "Формы", "Forms"),
            ],
        ),
        (
            ("CSS: ko'rinish va joylashuv", "CSS: внешний вид и вёрстка", "CSS: looks and layout"),
            [
                ("Ranglar va shriftlar", "Цвета и шрифты", "Colors and fonts"),
                ("Flexbox bilan joylashuv", "Вёрстка на Flexbox", "Layout with Flexbox"),
                ("Grid bilan tarmoq", "Сетка на Grid", "Grids with CSS Grid"),
                (
                    "Telefon va planshetga moslash",
                    "Адаптация под телефон и планшет",
                    "Adapting to phones and tablets",
                ),
            ],
        ),
        (
            ("JavaScript: jonli sahifa", "JavaScript: живая страница", "JavaScript: a live page"),
            [
                ("O'zgaruvchilar va shartlar", "Переменные и условия", "Variables and conditions"),
                ("Funksiyalar va massivlar", "Функции и массивы", "Functions and arrays"),
                ("Sahifa bilan ishlash (DOM)", "Работа со страницей (DOM)", "Working with the DOM"),
                ("Serverdan ma'lumot olish", "Получение данных с сервера", "Fetching data"),
            ],
        ),
        (
            ("React: zamonaviy interfeys", "React: современный интерфейс", "React: modern UI"),
            [
                ("Komponentlar", "Компоненты", "Components"),
                ("Holat va hodisalar", "Состояние и события", "State and events"),
                ("API bilan ishlash", "Работа с API", "Working with an API"),
            ],
        ),
        (
            ("Yakuniy loyiha", "Итоговый проект", "Final project"),
            [
                ("Loyiha rejasi", "План проекта", "Project plan"),
                ("Sahifani yig'amiz", "Собираем страницу", "Building the page"),
                ("Internetga joylash", "Публикация в интернете", "Publishing online"),
            ],
        ),
    ],
    "backend": [
        (
            ("Python asoslari", "Основы Python", "Python basics"),
            [
                ("Birinchi dastur", "Первая программа", "Your first program"),
                ("Ma'lumot turlari", "Типы данных", "Data types"),
                ("Funksiyalar va modullar", "Функции и модули", "Functions and modules"),
                ("Xatolarni ushlash", "Обработка ошибок", "Handling errors"),
            ],
        ),
        (
            ("Ma'lumotlar bazasi", "База данных", "The database"),
            [
                ("SQL asoslari", "Основы SQL", "SQL basics"),
                ("Jadvallar orasidagi bog'lanish", "Связи между таблицами", "Table relations"),
                ("So'rovlarni tezlatish", "Ускорение запросов", "Speeding up queries"),
            ],
        ),
        (
            ("Django va API", "Django и API", "Django and APIs"),
            [
                ("Loyiha tuzilmasi", "Структура проекта", "Project structure"),
                ("Modellar va migratsiyalar", "Модели и миграции", "Models and migrations"),
                ("REST API", "REST API", "REST APIs"),
                ("Autentifikatsiya", "Аутентификация", "Authentication"),
            ],
        ),
        (
            ("Deploy va kuzatuv", "Деплой и наблюдение", "Deployment and monitoring"),
            [
                ("Docker bilan yig'ish", "Сборка с Docker", "Building with Docker"),
                ("Serverga joylashtirish", "Развёртывание на сервере", "Deploying to a server"),
                ("Loglar va xatolar", "Логи и ошибки", "Logs and errors"),
            ],
        ),
    ],
    "suniy-intellekt": [
        (
            ("Ma'lumot bilan ishlash", "Работа с данными", "Working with data"),
            [
                ("Python va kutubxonalar", "Python и библиотеки", "Python and its libraries"),
                ("Ma'lumotni tozalash", "Очистка данных", "Cleaning data"),
                ("Grafiklar va tahlil", "Графики и анализ", "Charts and analysis"),
            ],
        ),
        (
            ("Mashinali o'qitish", "Машинное обучение", "Machine learning"),
            [
                ("Model nima qiladi", "Что делает модель", "What a model does"),
                ("O'qitish va tekshirish", "Обучение и проверка", "Training and validation"),
                ("Xatolarni kamaytirish", "Уменьшение ошибок", "Reducing errors"),
            ],
        ),
        (
            ("Tayyor AI xizmatlari", "Готовые AI-сервисы", "Ready-made AI services"),
            [
                ("Til modellari (LLM)", "Языковые модели (LLM)", "Language models (LLMs)"),
                ("Prompt va kontekst", "Промпт и контекст", "Prompts and context"),
                ("O'z ma'lumoti bilan (RAG)", "Со своими данными (RAG)", "Your own data (RAG)"),
            ],
        ),
        (
            ("Mahsulot qilish", "Превращаем в продукт", "Turning it into a product"),
            [
                ("API bilan ulash", "Подключение через API", "Connecting through an API"),
                ("Narx va tezlik", "Стоимость и скорость", "Cost and speed"),
                ("Yakuniy loyiha", "Итоговый проект", "Final project"),
            ],
        ),
    ],
    "praktikum-frontend": [
        (
            ("Ish tartibi", "Рабочий процесс", "How the work is organised"),
            [
                ("Git va jamoa", "Git и команда", "Git and the team"),
                ("Vazifa va muddat", "Задача и срок", "Tasks and deadlines"),
                ("Kod ko'rigi", "Код-ревью", "Code review"),
            ],
        ),
        (
            ("Birinchi loyiha", "Первый проект", "The first project"),
            [
                ("Dizayndan kodga", "От дизайна к коду", "From design to code"),
                ("Komponentlar kutubxonasi", "Библиотека компонентов", "A component library"),
                ("Testlar", "Тесты", "Tests"),
            ],
        ),
        (
            ("Ikkinchi loyiha", "Второй проект", "The second project"),
            [
                ("API bilan ishlash", "Работа с API", "Working with an API"),
                ("Tezlik va optimallash", "Скорость и оптимизация", "Speed and optimisation"),
                ("Portfolioga joylash", "Публикация в портфолио", "Publishing to a portfolio"),
            ],
        ),
    ],
    "praktikum-backend": [
        (
            ("Ish tartibi", "Рабочий процесс", "How the work is organised"),
            [
                ("Git va jamoa", "Git и команда", "Git and the team"),
                ("Talablarni o'qish", "Чтение требований", "Reading requirements"),
                ("Kod ko'rigi", "Код-ревью", "Code review"),
            ],
        ),
        (
            ("Servis yozamiz", "Пишем сервис", "Building a service"),
            [
                ("Ma'lumot modeli", "Модель данных", "The data model"),
                ("API va validatsiya", "API и валидация", "APIs and validation"),
                ("Testlar", "Тесты", "Tests"),
            ],
        ),
        (
            ("Ishga chiqarish", "Вывод в продакшн", "Going to production"),
            [
                ("Docker va CI", "Docker и CI", "Docker and CI"),
                ("Monitoring", "Мониторинг", "Monitoring"),
                ("Yuklamaga chidamlilik", "Устойчивость к нагрузке", "Handling load"),
            ],
        ),
    ],
    "ingliz-tili": [
        (
            ("Gapirishni boshlaymiz", "Начинаем говорить", "Starting to speak"),
            [
                ("Tanishuv va o'zi haqida", "Знакомство и о себе", "Introductions"),
                ("Kundalik savollar", "Повседневные вопросы", "Everyday questions"),
                ("Talaffuz", "Произношение", "Pronunciation"),
            ],
        ),
        (
            ("Grammatika kerakligicha", "Грамматика по необходимости", "Grammar as needed"),
            [
                ("Zamonlar", "Времена", "Tenses"),
                ("Savol va inkor", "Вопрос и отрицание", "Questions and negation"),
                ("Ko'p ishlatiladigan iboralar", "Частые фразы", "Common phrases"),
            ],
        ),
        (
            ("Ish uchun ingliz tili", "Английский для работы", "English for work"),
            [
                ("Ish suhbati", "Собеседование", "Job interviews"),
                ("Xat va xabar yozish", "Письма и сообщения", "Writing emails and messages"),
                ("IT atamalari", "IT-термины", "IT vocabulary"),
            ],
        ),
    ],
}

LESSON_MINUTES = 20


LEGAL: list[tuple[str, Tr]] = [
    ("offer", ("Ommaviy oferta", "Публичная оферта", "Public offer")),
    ("privacy", ("Maxfiylik siyosati", "Политика конфиденциальности", "Privacy policy")),
    ("refund-policy", ("Pulni qaytarish qoidalari", "Правила возврата", "Refund policy")),
]

LEGAL_BODY: Tr = (
    "<p>Bu namunaviy matn. Yakuniy matnni yurist tayyorlaydi va u admin paneldan "
    "joylashtiriladi.</p>",
    "<p>Это демонстрационный текст. Итоговый текст готовит юрист, он размещается через "
    "админ-панель.</p>",
    "<p>This is placeholder text. The final version is prepared by a lawyer and published "
    "from the admin panel.</p>",
)


class Command(BaseCommand):
    help = "Landing uchun namunaviy ma'lumotlar (faqat bo'sh jadvallarga)."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        self._site()
        self._ordered(
            Advantage, [{"icon": i, **tr("title", t), **tr("text", x)} for i, t, x in ADVANTAGES]
        )
        self._ordered(Concern, [{**tr("problem", p), **tr("answer", a)} for p, a in CONCERNS])
        self._ordered(HowStep, [{**tr("title", t), **tr("text", x)} for t, x in STEPS])
        self._ordered(FAQItem, [{**tr("question", q), **tr("answer", a)} for q, a in FAQ])
        self._catalog()
        self._programs()
        self._legal()
        self.stdout.write(self.style.SUCCESS("Namunaviy ma'lumotlar tayyor."))

    def _site(self) -> None:
        site = SiteSettings.load()
        changed = False
        for field, values in SITE.items():
            # Til ustunlarini modeltranslation dinamik qo'shadi, shuning uchun getattr.
            current = getattr(site, f"{field}_uz", "")
            if current and current != SiteSettings.DEFAULT_HERO_TITLE:
                continue
            for key, value in tr(field, values).items():
                setattr(site, key, value)
            changed = True
        if not site.phone:
            site.phone = "+998 90 000 00 00"
            changed = True
        if not site.email:
            site.email = "info@example.uz"
            changed = True
        if changed:
            site.save()

    def _ordered(self, model: Any, rows: list[dict[str, str]]) -> None:
        if model.objects.exists():
            return
        model.objects.bulk_create(model(order=index, **row) for index, row in enumerate(rows))

    def _catalog(self) -> None:
        if Course.objects.exists():
            return
        categories = {
            slug: Category.objects.create(slug=slug, order=index, **tr("name", names))
            for index, (slug, names) in enumerate(CATEGORIES)
        }
        for index, data in enumerate(COURSES):
            age_min, age_max = data.get("age", (None, None))
            Course.objects.create(
                slug=data["slug"],
                category=categories[data["category"]],
                level=data["level"],
                audience=data.get("audience", Course.Audience.ADULT),
                age_min=age_min,
                age_max=age_max,
                # Hamma kurs onlayn ham, offlayn ham o'qitiladi.
                study_format=Course.Format.BOTH,
                status=Course.Status.PUBLISHED,
                price_online=data["price_online"],
                price_offline_monthly=data["price_offline_monthly"],
                duration_hours=data["duration_hours"],
                video_language=data.get("video_language", "uz"),
                icon=data["icon"],
                is_featured=data.get("featured", False),
                order=index,
                **tr("title", data["title"]),
                **tr("short_description", data["short_description"]),
            )

    def _programs(self) -> None:
        """Kurs dasturi: modullar va darslar. Dasturi bor kursga tegilmaydi."""
        for course in Course.objects.filter(slug__in=PROGRAM, modules__isnull=True).distinct():
            self._program(course)

    def _program(self, course: Course) -> None:
        modules = PROGRAM.get(course.slug, [])
        for module_index, (module_title, lessons) in enumerate(modules):
            module = Module.objects.create(
                course=course, order=module_index, **tr("title", module_title)
            )
            for lesson_index, lesson_title in enumerate(lessons):
                Lesson.objects.create(
                    module=module,
                    order=lesson_index,
                    duration_min=LESSON_MINUTES,
                    is_preview=module_index == 0 and lesson_index == 0,
                    **tr("title", lesson_title),
                )

    def _legal(self) -> None:
        for slug, titles in LEGAL:
            LegalPage.objects.get_or_create(
                slug=slug, defaults={**tr("title", titles), **tr("body", LEGAL_BODY)}
            )
