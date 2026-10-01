from django.http import HttpRequest


def get_client_ip(request: HttpRequest) -> str | None:
    """Haqiqiy mijoz IP'si. nginx X-Forwarded-For oxiriga $remote_addr qo'shadi."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[-1].strip() or None
    return request.META.get("REMOTE_ADDR")
