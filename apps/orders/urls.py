from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    path("buy/<uuid:ticket_type_id>/", views.CreateOrderView.as_view(), name="create"),
    path("success/", views.order_success, name="success"),
    path("status/", views.order_status_api, name="status"),
    path("ticket/<str:token>/", views.ticket_detail, name="ticket-detail"),
]
