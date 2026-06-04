"""
YooKassa payment integration.

Flow:
  1. create_payment()  →  returns confirmation_url, redirect user
  2. YooKassa POSTs webhook  →  webhook_view  →  process_webhook_event.delay()
  3. process_webhook_event()  →  mark order paid, generate ticket, send email
"""
import logging
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
import yookassa
from yookassa import Configuration, Payment as YKPayment
from yookassa.domain.notification import WebhookNotificationFactory

from apps.events.models import TicketType
from apps.orders.models import Order
from apps.payments.models import Payment, WebhookEvent

logger = logging.getLogger(__name__)


def _configure():
    Configuration.account_id = settings.YOOKASSA_SHOP_ID
    Configuration.secret_key = settings.YOOKASSA_SECRET_KEY


def create_payment(order: Order) -> Payment:
    """Create YooKassa payment and persist it. Returns Payment instance."""
    _configure()

    idempotency_key = str(uuid.uuid4())

    payload = {
        "amount": {
            "value": str(order.total_amount),
            "currency": "RUB",
        },
        "confirmation": {
            "type": "redirect",
            "return_url": settings.YOOKASSA_RETURN_URL,
        },
        "capture": True,
        "description": f"Билет на мероприятие — заказ {order.order_number}",
        "metadata": {
            "order_id": str(order.id),
            "order_number": order.order_number,
        },
        "receipt": {
            "customer": {
                "email": order.customer.email,
            },
            "items": [
                {
                    "description": f"Билет {order.ticket_type.name}",
                    "quantity": str(order.quantity),
                    "amount": {
                        "value": str(order.unit_price),
                        "currency": "RUB",
                    },
                    "vat_code": 1,
                    "payment_mode": "full_prepayment",
                    "payment_subject": "service",
                }
            ],
        },
    }

    yk_payment = YKPayment.create(payload, idempotency_key)

    with transaction.atomic():
        payment = Payment.objects.create(
            order=order,
            yookassa_payment_id=yk_payment.id,
            amount=order.total_amount,
            status=Payment.STATUS_PENDING,
            confirmation_url=yk_payment.confirmation.confirmation_url,
            raw_response=yk_payment.json(),
        )

    logger.info(
        "payment_created",
        extra={"order_number": order.order_number, "payment_id": yk_payment.id},
    )
    return payment


def process_webhook_event(webhook_event: WebhookEvent) -> None:
    """
    Called from Celery task. Parse event, update Order/Payment state.
    Idempotent — safe to call multiple times with the same event.
    """
    event_type = webhook_event.event_type
    body = webhook_event.raw_body

    handler = {
        "payment.succeeded": _handle_payment_succeeded,
        "payment.canceled": _handle_payment_canceled,
        "refund.succeeded": _handle_refund_succeeded,
    }.get(event_type)

    if handler is None:
        logger.info("webhook_skipped", extra={"event_type": event_type})
        webhook_event.status = WebhookEvent.STATUS_SKIPPED
        webhook_event.save(update_fields=["status"])
        return

    try:
        handler(body)
        webhook_event.status = WebhookEvent.STATUS_PROCESSED
    except Exception as exc:
        webhook_event.status = WebhookEvent.STATUS_FAILED
        webhook_event.error = str(exc)
        logger.exception(
            "webhook_processing_failed",
            extra={"event_id": webhook_event.event_id, "error": str(exc)},
        )
        raise
    finally:
        webhook_event.save(update_fields=["status", "error", "updated_at"])


def _handle_payment_succeeded(body: dict) -> None:
    payment_obj = body.get("object", {})
    yk_payment_id = payment_obj.get("id")
    if not yk_payment_id:
        raise ValueError("Missing payment id in webhook body")

    with transaction.atomic():
        # Lock payment row to prevent concurrent processing
        try:
            payment = Payment.objects.select_for_update().get(
                yookassa_payment_id=yk_payment_id
            )
        except Payment.DoesNotExist:
            logger.error("payment_not_found", extra={"yk_payment_id": yk_payment_id})
            raise

        if payment.status == Payment.STATUS_SUCCEEDED:
            logger.info("payment_already_succeeded", extra={"yk_payment_id": yk_payment_id})
            return  # idempotent

        payment.status = Payment.STATUS_SUCCEEDED
        payment.paid_at = timezone.now()
        payment.raw_response = payment_obj
        payment.save(update_fields=["status", "paid_at", "raw_response", "updated_at"])

        order = payment.order
        order.status = Order.STATUS_PAID
        order.save(update_fields=["status", "updated_at"])

        # Release reservation, increment sold count atomically (F expressions
        # avoid read-modify-write races under concurrent webhooks).
        from django.db.models import F, Value
        from django.db.models.functions import Greatest
        TicketType.objects.filter(pk=order.ticket_type_id).update(
            sold_quantity=F("sold_quantity") + order.quantity,
            reserved_quantity=Greatest(
                F("reserved_quantity") - order.quantity, Value(0)
            ),
            updated_at=timezone.now(),
        )

    # Trigger async post-payment tasks (outside transaction)
    from tasks.payment_tasks import on_payment_succeeded
    on_payment_succeeded.delay(str(order.id))


def _handle_payment_canceled(body: dict) -> None:
    yk_payment_id = body.get("object", {}).get("id")
    with transaction.atomic():
        try:
            payment = Payment.objects.select_for_update().get(
                yookassa_payment_id=yk_payment_id
            )
        except Payment.DoesNotExist:
            return

        if payment.status in (Payment.STATUS_CANCELED,):
            return

        payment.status = Payment.STATUS_CANCELED
        payment.save(update_fields=["status", "updated_at"])

        order = payment.order
        order.status = Order.STATUS_CANCELED
        order.save(update_fields=["status", "updated_at"])

        # Release reservation
        tt = order.ticket_type
        tt.reserved_quantity = max(0, tt.reserved_quantity - order.quantity)
        tt.save(update_fields=["reserved_quantity", "updated_at"])


def _handle_refund_succeeded(body: dict) -> None:
    refund_obj = body.get("object", {})
    yk_payment_id = refund_obj.get("payment_id")
    refund_amount = Decimal(refund_obj.get("amount", {}).get("value", "0"))

    with transaction.atomic():
        try:
            payment = Payment.objects.select_for_update().get(
                yookassa_payment_id=yk_payment_id
            )
        except Payment.DoesNotExist:
            return

        payment.status = Payment.STATUS_REFUNDED
        payment.refunded_at = timezone.now()
        payment.refund_amount = refund_amount
        payment.save(update_fields=["status", "refunded_at", "refund_amount", "updated_at"])

        order = payment.order
        order.status = Order.STATUS_REFUNDED
        order.save(update_fields=["status", "updated_at"])

        # Cancel all tickets for this order
        order.tickets.update(status="canceled")


def create_refund(payment: Payment, amount: Decimal | None = None) -> dict:
    """Initiate a refund via YooKassa API."""
    _configure()
    refund_amount = amount or payment.amount
    result = yookassa.Refund.create({
        "payment_id": payment.yookassa_payment_id,
        "amount": {"value": str(refund_amount), "currency": "RUB"},
    })
    return result.json()
