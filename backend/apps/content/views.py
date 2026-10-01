from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import LegalPage
from .serializers import LegalPageSerializer, SitePayloadSerializer
from .services import get_site_payload

LANGUAGE_HEADER = OpenApiParameter(
    name="Accept-Language",
    location=OpenApiParameter.HEADER,
    description="uz, ru yoki en",
    required=False,
)


class SiteView(APIView):
    """Landing uchun barcha ma'lumot bitta so'rovda.

    Throttle yo'q: so'rovlar Next.js serveridan keladi (hamma foydalanuvchilar uchun bitta IP)
    va javob keshlangan. Umumiy IP limiti nginx darajasida.
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    @extend_schema(responses=SitePayloadSerializer, parameters=[LANGUAGE_HEADER], tags=["content"])
    def get(self, request: Request) -> Response:
        return Response(get_site_payload())


@extend_schema(parameters=[LANGUAGE_HEADER], tags=["content"])
class LegalPageView(RetrieveAPIView[LegalPage]):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []
    queryset = LegalPage.objects.all()
    serializer_class = LegalPageSerializer
    lookup_field = "slug"
