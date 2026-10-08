from django.urls import path

from relay.views import Health, IncidentDetail, IncidentReview, Incidents, Ready

urlpatterns = [
    path("health/", Health.as_view()),
    path("ready/", Ready.as_view()),
    path("api/incidents/", Incidents.as_view()),
    path("api/incidents/<uuid:incident_id>/", IncidentDetail.as_view()),
    path("api/incidents/<uuid:incident_id>/review/", IncidentReview.as_view()),
]
