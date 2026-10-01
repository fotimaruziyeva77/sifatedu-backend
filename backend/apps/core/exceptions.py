"""API xatolarini yagona formatga keltirish: `{"error": {"code", "message", "fields"?}}`."""

import math
from typing import Any

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.utils.translation import gettext as _
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    # DRF Django istisnolarini ichkarida o'giradi; kodni to'g'ri olish uchun oldinroq o'giramiz.
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    response = exception_handler(exc, context)
    if response is None:
        # Kutilmagan xato: Django'ning 500 handler'i va Sentry ishlaydi.
        return None

    if isinstance(exc, exceptions.ValidationError):
        error: dict[str, Any] = {
            "code": "validation_error",
            "message": _("Ma'lumotlarda xatolik bor."),
            "fields": response.data,
        }
    else:
        code = exc.get_codes() if isinstance(exc, exceptions.APIException) else "error"
        detail = getattr(exc, "detail", exc)
        error = {
            "code": code if isinstance(code, str) else "error",
            "message": str(detail),
        }
        # Limitga tushganda frontend taymer ko'rsatadi.
        wait = getattr(exc, "wait", None) if isinstance(exc, exceptions.Throttled) else None
        if wait:
            error["retry_after"] = math.ceil(wait)

    response.data = {"error": error}
    return response
