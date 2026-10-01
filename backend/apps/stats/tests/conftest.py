import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def clean_cache() -> None:
    """Xato hisoblagichlari keshda: boshqa testlarning xatolari bu yerga o'tmasin."""
    cache.clear()
