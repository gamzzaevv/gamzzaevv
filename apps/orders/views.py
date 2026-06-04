import logging
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View

from apps.events.models import TicketType
from apps.orders.forms import OrderForm
from apps.orders.models import Order, Ticket
from apps.orders.service import create_order
from apps.payments.service import create_payment

logger = logging.getLogger(__name__)


class CreateOrderView(View):
    template_name = "orders/create.html"

    def get(self, request, ticket_type_id):
        tt = get_object_or_404(TicketType, pk=ticket_type_id, is_visible=True)
        form = OrderForm(ticket_type=tt)
        return render(request, self.template_name, {"form": form, "ticket_type": tt})

    def post(self, request, ticket_type_id):
        tt = get_object_or_404(TicketType, pk=ticket_type_id, is_visible=True)
        form = OrderForm(request.POST, ticket_type=tt)

        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "ticket_type": tt})

        d = form.cleaned_data
        ip = _get_ip(request)

        try:
            order = create_order(
                ticket_type=tt,
                quantity=d.get("quantity", 1),
                first_name=d["first_name"],
                last_name=d["last_name"],
                patronymic=d.get("patronymic", ""),
                email=d["email"],
                phone=d.get("phone", ""),
                promo_code=d.get("promo_code"),
                ip_address=ip,
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                consent=d["consent"],
            )
        except ValueError as exc:
            form.add_error(None, str(exc))
            return render(request, self.template_name, {"form": form, "ticket_type": tt})

        try:
            payment = create_payment(order)
        except Exception:
            logger.exception("payment_creation_failed", extra={"order_id": str(order.id)})
            messages.error(request, "Не удалось создать платёж. Попробуйте ещё раз.")
            return render(request, self.template_name, {"form": form, "ticket_type": tt})

        return redirect(payment.confirmation_url)


def order_success(request):
    """
    Landing page after returning from YooKassa.

    IMPORTANT: returning here does NOT mean the payment succeeded — YooKassa
    redirects here regardless of outcome, and the real confirmation arrives
    asynchronously via webhook. So we render the actual order status and let
    the page poll /orders/status/ until the webhook lands.
    """
    order_number = request.GET.get("order")
    order = None
    if order_number:
        order = (
            Order.objects.select_related("customer")
            .filter(order_number=order_number)
            .first()
        )
    return render(request, "orders/success.html", {"order": order})


def order_status_api(request):
    """Lightweight JSON endpoint polled by the success page."""
    order_number = request.GET.get("order", "")
    order = Order.objects.filter(order_number=order_number).first()
    if not order:
        return JsonResponse({"found": False}, status=404)
    return JsonResponse({
        "found": True,
        "status": order.status,
        "is_paid": order.status == Order.STATUS_PAID,
        "order_number": order.order_number,
        "email": order.customer.email,
    })


def ticket_detail(request, token):
    ticket = get_object_or_404(Ticket, token=token)
    return render(request, "tickets/detail.html", {"ticket": ticket})


def _get_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
