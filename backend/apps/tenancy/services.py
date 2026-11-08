from collections.abc import Iterable

from django_tenants.utils import get_public_schema_name

from .models import Center, Domain


def ensure_center(schema: str, name: str, domains: Iterable[str]) -> Center:
    """Markaz va manzillari (qayta chaqirish xavfsiz). Sxema yo'q bo'lsa — yaratiladi va
    migratsiyalar o'tkaziladi. Birinchi manzil — asosiy."""
    center = Center.objects.filter(schema_name=schema).first()
    if center is None:
        center = Center(schema_name=schema, name=name)
        center.save(verbosity=0)  # type: ignore[call-arg]  # TenantMixin.save
    for index, domain in enumerate(domains):
        Domain.objects.get_or_create(
            domain=domain, defaults={"tenant": center, "is_primary": index == 0}
        )
    return center


def ensure_platform(domain: str) -> Center:
    """`public` sxema ham jadvalda turadi: platforma manzili va faqat `public`da bajariladigan
    rejali vazifalar shu qator orqali topiladi."""
    return ensure_center(get_public_schema_name(), "Platforma", [domain])
