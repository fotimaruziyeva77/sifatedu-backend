"""Admin panel doim o'zbekcha.

Admin matnlari (bo'limlar, maydonlar, statistika) faqat o'zbekcha yozilgan, `LocaleMiddleware` esa
tilni brauzerdan oladi: ruscha yoki inglizcha brauzerda tugmalar boshqa tilda, qolgani o'zbekcha
chiqardi. Shuning uchun `/admin/` da til — `LANGUAGE_CODE`.
"""

from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.urls import reverse
from django.utils import translation


class AdminLanguageMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self.prefix = ""

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not self.prefix:
            self.prefix = reverse("admin:index")
        if request.path.startswith(self.prefix):
            translation.activate(settings.LANGUAGE_CODE)
            request.LANGUAGE_CODE = settings.LANGUAGE_CODE
        return self.get_response(request)
