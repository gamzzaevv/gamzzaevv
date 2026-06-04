from django.shortcuts import render
from .models import Event


def landing(request):
    event = Event.objects.filter(is_published=True, is_active=True).order_by("-starts_at").first()
    ticket_types = []
    if event:
        ticket_types = event.ticket_types.filter(is_visible=True).order_by("sort_order")
    return render(request, "landing/index.html", {
        "event": event,
        "ticket_types": ticket_types,
    })
