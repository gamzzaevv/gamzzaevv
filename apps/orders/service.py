"""Business logic for order creation and ticket management."""
import datetime
import logging
from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.events.models import TicketType, PromoCode
from apps.orders.models import Customer, Order, Ticket, ConsentLog

logger = logging.getLogger(__name__)

RESERVATION_MINUTES = 15


def create_order(
    *,
    ticket_type: TicketType,
    quantity: int,
    first_name: str,
    last_name: str,
    patronymic: str = "",
    email: str,
    phone: str = "",
    promo_code: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: str = "",
    consent: bool = False,
) -> Order:
    """
    Atomically:
    - Validate availability (SELECT FOR UPDATE on TicketType)
    - Reserve seats
    - Create Customer + Order
    - Log consent
    """
    if not consent:
        raise ValueError("Требуется согласие на обработку персональных данных")

    with transaction.atomic():
        # Lock ticket type row to prevent overselling
        tt = TicketType.objects.select_for_update().get(pk=ticket_type.pk)

        if not tt.is_visible:
            raise ValueError("Билет недоступен")

        if tt.available_quantity < quantity:
            raise ValueError(
                f"Недостаточно билетов. Доступно: {tt.available_quantity}"
            )

        # Resolve promo code
        promo = None
        discount = Decimal("0")
        if promo_code:
            try:
                promo = PromoCode.objects.select_for_update().get(code=promo_code.upper())
                if not promo.is_valid():
                    raise ValueError("Промокод недействителен")
            except PromoCode.DoesNotExist:
                raise ValueError("Промокод не найден")

        unit_price = tt.price
        if promo:
            discounted_price = promo.apply(unit_price)
            discount = (unit_price - discounted_price) * quantity
            unit_price = discounted_price

        total = unit_price * quantity

        # Customer (reuse by email if exists)
        customer, _ = Customer.objects.get_or_create(
            email=email.lower(),
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "patronymic": patronymic,
                "phone": phone,
                "consent_given_at": timezone.now(),
                "consent_ip": ip_address,
                "offer_accepted_at": timezone.now(),
            },
        )

        order = Order.objects.create(
            order_number=Order.generate_order_number(),
            customer=customer,
            ticket_type=tt,
            promo_code=promo,
            quantity=quantity,
            unit_price=tt.price,
            discount_amount=discount,
            total_amount=total,
            expires_at=timezone.now() + datetime.timedelta(minutes=RESERVATION_MINUTES),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Reserve seats
        tt.reserved_quantity += quantity
        tt.save(update_fields=["reserved_quantity", "updated_at"])

        # Increment promo usage
        if promo:
            promo.used_count += 1
            promo.save(update_fields=["used_count", "updated_at"])

        # Consent audit log
        ConsentLog.objects.create(
            customer=customer,
            consent_type="personal_data_and_offer",
            document_version="1.0",
            ip_address=ip_address or "0.0.0.0",
            user_agent=user_agent,
        )

    logger.info(
        "order_created",
        extra={"order_number": order.order_number, "email": email, "total": str(total)},
    )
    return order


def create_tickets_for_order(order: Order) -> list[Ticket]:
    """Create Ticket records for a paid order (idempotent)."""
    existing = list(order.tickets.all())
    if existing:
        return existing

    tickets = []
    for i in range(order.quantity):
        idx = i + 1
        ticket = Ticket.objects.create(
            order=order,
            ticket_number=f"{order.order_number}-{idx:02d}",
            token=Ticket.generate_token(),
            verify_code=Ticket.generate_verify_code(),
        )
        tickets.append(ticket)

    return tickets
