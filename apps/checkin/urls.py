from django.urls import path
from . import views

app_name = "checkin"

urlpatterns = [
    path("", views.CheckInView.as_view(), name="scanner"),
    path("validate/", views.validate_ticket_api, name="validate"),
    path("verify/<str:token>/", views.verify_ticket_public, name="public-verify"),
]
