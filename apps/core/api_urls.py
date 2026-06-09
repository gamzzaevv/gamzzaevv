from django.urls import path, include

urlpatterns = [
    path("events/", include("apps.events.api_urls")),
    path("orders/", include("apps.orders.api_urls")),
    path("checkin/", include("apps.checkin.api_urls")),
]
