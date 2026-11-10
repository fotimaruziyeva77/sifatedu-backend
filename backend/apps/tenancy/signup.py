"""Markazni egasi o'zi ochadi: manzil qoidalari, ariza va markazni tayyorlash."""

import logging
import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.utils import timezone
from django_tenants.utils import schema_context

from .models import Center, Domain, Plan, Signup

logger = logging.getLogger(__name__)

# Kamida 3, ko'pi bilan 30 belgi; lotin harfi bilan boshlanadi; ketma-ket chiziqcha yo'q.
SLUG = re.compile(r"^[a-z](?!.*--)[a-z0-9-]{1,28}[a-z0-9]$")
# Telegram HTML va tarjima shablonlarini buzadigan belgilar.
NAME_FORBIDDEN = re.compile(r"[<>{}&]")
# Xizmat manzillari va adashtiradigan nomlar.
RESERVED = frozenset(
    [
        "www",
        "admin",
        "api",
        "app",
        "apps",
        "platform",
        "media",
        "static",
        "assets",
        "cdn",
        "files",
        "storage",
        "mail",
        "webmail",
        "smtp",
        "imap",
        "pop",
        "ftp",
        "ns",
        "ns1",
        "ns2",
        "dns",
        "vpn",
        "git",
        "status",
        "blog",
        "docs",
        "help",
        "support",
        "billing",
        "pay",
        "payment",
        "payments",
        "click",
        "auth",
        "login",
        "signup",
        "register",
        "dashboard",
        "test",
        "demo",
        "staging",
        "dev",
        "sifat",
        "sifatedu",
        "public",
        "root",
        "system",
        "telegram",
        "bot",
    ]
)
# Sxema nomi har doim shu bilan boshlanadi: PostgreSQL nomlari va mavjud sxemalar band emas.
SCHEMA_PREFIX = "c_"
WELCOME_TTL = 15 * 60


class Address:
    INVALID = "invalid"
    RESERVED = "reserved"
    TAKEN = "taken"


class AddressTaken(Exception):
    """Manzil tasdiqlash paytida band bo'lib qoldi."""


class PhoneTaken(Exception):
    """Bu raqam bilan markaz allaqachon ochilgan."""


def schema_for(slug: str) -> str:
    return SCHEMA_PREFIX + slug.replace("-", "_")


def domain_for(slug: str) -> str:
    return f"{slug}.{settings.CENTERS_BASE_DOMAIN}"


def address_problem(slug: str) -> str | None:
    """Manzilni olib bo'lmasa — sababi (`Address`), bo'lsa — None."""
    if not SLUG.match(slug):
        return Address.INVALID
    if slug in RESERVED:
        return Address.RESERVED
    taken = (
        Domain.objects.filter(domain=domain_for(slug)).exists()
        or Center.objects.filter(schema_name=schema_for(slug)).exists()
        or Signup.objects.filter(slug=slug, status__in=Signup.TAKEN).exists()
    )
    return Address.TAKEN if taken else None


def create_signup(
    *,
    plan: Plan,
    name: str,
    slug: str,
    first_name: str,
    phone: str,
    password: str,
    locale: str,
    last_name: str = "",
) -> Signup:
    """Kod tasdiqlanguncha ariza hech narsani band qilmaydi va boshqa arizalarga tegmaydi:
    raqamni bilgan begona odam birovning arizasini bekor qila olmaydi. Tugallanmaganlari —
    `tasks.purge_signups`."""
    return Signup.objects.create(
        plan=plan,
        name=name,
        slug=slug,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        password_hash=make_password(password),
        locale=locale,
    )


def confirm(signup: Signup) -> None:
    """SMS kod to'g'ri: manzil va raqam band qilinadi, markaz fonda tayyorlanadi."""
    if Center.objects.filter(owner_phone=signup.phone).exists():
        raise PhoneTaken
    if address_problem(signup.slug):
        raise AddressTaken
    try:
        with transaction.atomic():
            signup.status = Signup.Status.PREPARING
            signup.save(update_fields=["status", "updated_at"])
    except IntegrityError as exc:
        signup.status = Signup.Status.PENDING
        taken = Signup.objects.filter(phone=signup.phone, status__in=Signup.TAKEN).exists()
        raise (PhoneTaken if taken else AddressTaken) from exc

    transaction.on_commit(lambda: _enqueue(signup.pk))


def _enqueue(signup_id: int) -> None:
    """Navbat ishlamasa ham javob qaytadi: ariza qotib qolsa, `fail_stuck_signups` yopadi."""
    from .tasks import provision_center

    try:
        provision_center.delay(signup_id)
    except Exception:
        logger.exception("Markaz tayyorlash navbatga qo'yilmadi: ariza #%s", signup_id)


def _welcome_key(token: str) -> str:
    return f"center:welcome:{token}"


def _url_key(signup: Signup) -> str:
    return f"signup:url:{signup.token}"


def take_welcome(token: str) -> int | None:
    """Egasini kabinetga bir marta kiritadi: ikki parallel so'rovdan faqat bittasi oladi."""
    key = _welcome_key(token)
    user_id = cache.get(key)
    if user_id is None or not cache.delete(key):
        return None
    return int(user_id)


def ready_url(signup: Signup) -> str:
    """Bir martalik kirish havolasi; muddati o'tgan bo'lsa — kirish sahifasi."""
    login = (
        f"{settings.SITE_SCHEME}://{domain_for(signup.slug)}{settings.SITE_PORT}"
        f"/{signup.locale}/auth/login"
    )
    return str(cache.get(_url_key(signup)) or login)


def _site_defaults(name: str) -> None:
    from apps.content.models import SiteSettings

    subtitles = {
        "uz": "Zamonaviy o'quv markazi: kurslar, tajribali ustozlar va qulay jadval.",
        "ru": "Современный учебный центр: курсы, опытные преподаватели и удобное расписание.",
        "en": "A modern training center: courses, experienced teachers and a convenient schedule.",
    }
    values = {
        "hero_title": name,
        **{f"hero_title_{code}": name for code in subtitles},
        **{f"hero_subtitle_{code}": text for code, text in subtitles.items()},
    }
    SiteSettings.objects.update_or_create(pk=1, defaults=values)


def _create_owner(signup: Signup) -> int:
    """Egasi: hamma ruxsat (ADMIN) va statistika (DIRECTOR)."""
    from apps.users.models import User
    from apps.users.roles import Role, set_roles

    owner, _created = User.objects.get_or_create(
        phone=signup.phone,
        defaults={
            "first_name": signup.first_name,
            "last_name": signup.last_name,
            "password": signup.password_hash,
            "locale": signup.locale,
        },
    )
    set_roles(owner, [Role.ADMIN, Role.DIRECTOR])
    return owner.pk


def discard(signup: Signup) -> None:
    """Yarim ochilgan markaz qolmasin: manzil bo'shaydi va ega qayta urina oladi.

    Faqat ariza tasdiqlangandan keyin yaratilgan markaz o'chiriladi: tasdiq paytida bu sxema
    yo'q edi (`address_problem`), undan oldin yaratilganiga esa hech qachon tegilmaydi."""
    center = Center.objects.filter(
        schema_name=schema_for(signup.slug), created_at__gte=signup.updated_at
    ).first()
    if center is not None:
        center.delete(force_drop=True)  # type: ignore[call-arg]  # TenantMixin.delete


def provision(signup: Signup) -> Center:
    """Markazni ochadi: sxema (migratsiyalar bilan), tarif va sinov muddati, egasi, sayt matni."""
    plan = signup.plan
    schema = schema_for(signup.slug)
    # Oldingi urinish (to'xtatilgan vazifa) qoldirgan yarim sxema qayta ishlatilmaydi.
    discard(signup)
    if Center.objects.filter(schema_name=schema).exists():
        # Mavjud markazga egalik berilmaydi: ariza «xato» bo'ladi.
        raise RuntimeError(f"Sxema band: {schema}")
    center = Center(
        schema_name=schema,
        name=signup.name,
        plan=plan,
        paid_until=timezone.localdate() + timedelta(days=plan.trial_days),
        is_trial=True,
        owner_name=f"{signup.first_name} {signup.last_name}".strip(),
        owner_phone=signup.phone,
    )
    # Sxema yaratiladi va migratsiyalar o'tadi; xato bo'lsa, o'zi tozalaydi (`TenantMixin.save`).
    center.save(verbosity=0)  # type: ignore[call-arg]
    Domain.objects.create(domain=domain_for(signup.slug), tenant=center, is_primary=True)

    token = secrets.token_urlsafe(32)
    with schema_context(center.schema_name):
        _site_defaults(signup.name)
        owner_id = _create_owner(signup)
        cache.set(_welcome_key(token), owner_id, WELCOME_TTL)
    base = f"{settings.SITE_SCHEME}://{domain_for(signup.slug)}{settings.SITE_PORT}"
    cache.set(_url_key(signup), f"{base}/api/v1/center/welcome/{token}/", WELCOME_TTL)

    signup.status = Signup.Status.READY
    signup.center = center
    signup.password_hash = ""
    signup.save(update_fields=["status", "center", "password_hash", "updated_at"])
    return center
