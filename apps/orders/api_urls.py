from django.urls import path
from .api_views import ValidatePromoView

urlpatterns = [
    path("promo/validate/", ValidatePromoView.as_view(), name="promo-validate"),
]
