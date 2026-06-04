"""Celery tasks for payment lifecycle."""
import logging

from celery import shared_task
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=30,
    acks_late=True,
    name="payments.process_webhook",
)
def process_webhook(self, webhook_event_id: str):
    """Deserialise and process a stored WebhookEvent."""
    from apps.payments.models import WebhookEvent
    from apps.payments.service import process_webhook_event

    try:
        event = WebhookEvent.objects.get(id=webhook_event_id)
    except WebhookEvent.DoesNotExist:
        logger.error("webhook_event_not_found", extra={"id": webhook_event_id})
        return

    try:
        process_webhook_event(event)
    except Exception as exc:
        logger.exception("webhook_task_error", extra={"webhook_event_id": webhook_event_id})
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    name="payments.on_payment_succeeded",
)
def on_payment_succeeded(self, order_id: str):
    """
    Post-payment orchestration:
    1. Create Ticket records
    2. Generate PDF + QR
    3. Send confirmation email
    """
    from apps.orders.models import Order, Ticket
    from apps.orders.service import create_tickets_for_order

    try:
        order = Order.objects.select_related(
            "customer", "ticket_type__event"
        ).get(id=order_id)
    except Order.DoesNotExist:
        logger.error("order_not_found_post_payment", extra={"order_id": order_id})
        return

    try:
        with transaction.atomic():
            tickets = create_tickets_for_order(order)

        for ticket in tickets:
            generate_ticket_pdf.delay(str(ticket.id))

    except Exception as exc:
        logger.exception("post_payment_failed", extra={"order_id": order_id})
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    acks_late=True,
    name="payments.generate_ticket_pdf",
)
def generate_ticket_pdf(self, ticket_id: str):
    """Generate PDF, save to storage, then send email."""
    from apps.orders.models import Ticket
    from apps.orders.pdf_generator import generate_pdf
    from tasks.email_tasks import send_ticket_email

    try:
        ticket = Ticket.objects.select_related(
            "order__customer", "order__ticket_type__event"
        ).get(id=ticket_id)
    except Ticket.DoesNotExist:
        return

    try:
        generate_pdf(ticket)
        send_ticket_email.delay(str(ticket.id))
    except Exception as exc:
        logger.exception("pdf_generation_failed", extra={"ticket_id": ticket_id})
        raise self.retry(exc=exc)
