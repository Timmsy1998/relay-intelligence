from uuid import UUID

from pymongo.errors import PyMongoError
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from relay.repository import Conflict, database, repository


class Submission(serializers.Serializer):
    title = serializers.CharField(max_length=160, min_length=8)
    description = serializers.CharField(max_length=12000, min_length=20)
    service = serializers.CharField(max_length=80)
    severity = serializers.ChoiceField(choices=["P1", "P2", "P3"])


class Review(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["accepted", "rejected"])
    note = serializers.CharField(max_length=2000, allow_blank=True, default="")
    version = serializers.IntegerField(min_value=1)


class Health(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"status": "ok", "service": "relay-api"})


class Ready(Health):
    def get(self, request):
        try:
            database().command("ping")
        except PyMongoError:
            return Response({"status": "unavailable"}, status=503)
        return Response({"status": "ready"})


class Incidents(APIView):
    def get(self, request):
        return Response({"items": repository().list(), "limit": 100})

    def post(self, request):
        serializer = Submission(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_key = request.headers.get("Idempotency-Key", "")
        try:
            UUID(request_key)
        except (ValueError, TypeError):
            return Response({"detail": "Idempotency-Key must be a UUID."}, status=400)
        try:
            incident, created = repository().create(serializer.validated_data, request_key)
        except Conflict as exc:
            return Response({"detail": str(exc)}, status=409)
        return Response(incident, status=status.HTTP_202_ACCEPTED if created else 200)


class IncidentDetail(APIView):
    def get(self, request, incident_id):
        incident = repository().get(str(incident_id))
        return (
            Response(incident)
            if incident
            else Response({"detail": "Incident not found."}, status=404)
        )


class IncidentReview(APIView):
    def post(self, request, incident_id):
        serializer = Review(data=request.data)
        serializer.is_valid(raise_exception=True)
        if repository().get(str(incident_id)) is None:
            return Response({"detail": "Incident not found."}, status=404)
        try:
            incident = repository().review(str(incident_id), **serializer.validated_data)
        except Conflict as exc:
            return Response({"detail": str(exc)}, status=409)
        return Response(incident)
