from django.shortcuts import render
from .models import Event


def landing(request):
    fight_days = list(
        Event.objects.filter(is_published=True, is_active=True)
        .prefetch_related("ticket_types")
        .order_by("starts_at")
    )
    event = fight_days[0] if fight_days else None
    return render(request, "landing/index.html", {
        "event": event,
        "fight_days": fight_days,
    })
