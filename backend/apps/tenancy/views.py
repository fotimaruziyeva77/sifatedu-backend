from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .access import current_center
from .models import Center
from .sections import Feature


class CenterInfoSerializer(serializers.Serializer):
    state = serializers.ChoiceField(choices=Center.State.choices)
    features = serializers.ListField(child=serializers.ChoiceField(choices=Feature.choices))


class CenterInfoView(APIView):
    """Sayt shu javobga qarab menyu va sahifalarni ko'rsatadi."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []
    open_when_blocked = True

    @extend_schema(responses=CenterInfoSerializer, tags=["center"])
    def get(self, request: Request) -> Response:
        center = current_center()
        state = center.state if center else Center.State.ACTIVE
        features = center.features if center else frozenset(Feature.values)
        return Response({"state": state, "features": sorted(features)})
