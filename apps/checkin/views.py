from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views import View

from apps.checkin.service import validate_ticket
from apps.orders.models import Ticket


class CheckerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and (
            self.request.user.is_staff or self.request.user.is_checker
        )


class CheckInView(CheckerRequiredMixin, View):
    """QR scanner page — works in mobile browser via camera."""
    template_name = "checkin/scanner.html"

    def get(self, request):
        return render(request, self.template_name)


@login_required
@require_POST
def validate_ticket_api(request):
    """AJAX endpoint called by the scanner page."""
    if not (request.user.is_staff or request.user.is_checker):
        return JsonResponse({"error": "Forbidden"}, status=403)

    token = request.POST.get("token", "").strip()
    if not token:
        return JsonResponse({"error": "Token required"}, status=400)

    result = validate_ticket(
        token=token,
        scanned_by=request.user.email,
        ip_address=_get_ip(request),
        device_info=request.META.get("HTTP_USER_AGENT", "")[:255],
    )
    return JsonResponse(result)


def verify_ticket_public(request, token):
    """
    Public verify page — accessible via QR link.
    Shows ticket info but does NOT mark as used (read-only).
    """
    try:
        ticket = Ticket.objects.select_related(
            "order__customer", "order__ticket_type__event"
        ).get(token=token)
    except Ticket.DoesNotExist:
        ticket = None
    return render(request, "checkin/public_verify.html", {"ticket": ticket})


def _get_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
