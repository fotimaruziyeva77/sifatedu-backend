from django.core.files.storage import Storage, storages


def public_storage() -> Storage:
    """Ochiq fayllar (kurs muqovasi, ustoz rasmi): imzosiz URL bilan beriladi."""
    return storages["public"]
