from django.urls import path
from .views import validate_ticket_api

urlpatterns = [
    path("validate/", validate_ticket_api, name="checkin-validate"),
]
