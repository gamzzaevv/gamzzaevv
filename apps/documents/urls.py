from django.urls import path
from . import views

app_name = "documents"

urlpatterns = [
    path("<slug:slug>/", views.document_view, name="page"),
]
