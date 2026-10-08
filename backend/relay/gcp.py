"""Dedicated private Cloud Run Pub/Sub receiver. Never mount on the public API."""

import base64
import binascii
import json

from django.urls import path
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from relay.telemetry import emit
from relay.worker import process


class PubSubPush(APIView):
    # Cloud Run IAM authenticates Google's signed OIDC push token before Django.
    # The deployment must use --no-allow-unauthenticated.
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        try:
            encoded = request.data["message"]["data"]
            event = json.loads(base64.b64decode(encoded, validate=True))
            process(event)
        except (KeyError, TypeError, ValueError, binascii.Error):
            return Response({"detail": "Invalid event envelope"}, status=400)
        except Exception as exc:
            emit("pubsub.failed", error_type=type(exc).__name__)
            return Response({"detail": "Retry delivery"}, status=503)
        return Response(status=204)


urlpatterns = [path("pubsub/", PubSubPush.as_view())]
