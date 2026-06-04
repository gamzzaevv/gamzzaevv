"""Celery tasks for email delivery."""
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,
    acks_late=True,
    name="emails.send_ticket_email",
)
def send_ticket_email(self, ticket_id: str):
    from apps.orders.models import Ticket
    from apps.notifications.service import send_ticket_confirmation

    try:
        ticket = Ticket.objects.select_related(
            "order__customer", "order__ticket_type__event"
        ).get(id=ticket_id)
    except Ticket.DoesNotExist:
        return

    try:
        send_ticket_confirmation(ticket)
        ticket.email_sent_at = timezone.now()
        ticket.save(update_fields=["email_sent_at", "updated_at"])
    except Exception as exc:
        logger.exception("email_send_failed", extra={"ticket_id": ticket_id})
        raise self.retry(exc=exc)


@shared_task(name="emails.retry_failed_emails")
def retry_failed_emails():
    """Periodic task: retry emails not yet sent after 10 minutes."""
    from apps.orders.models import Ticket, Order
    from django.utils import timezone
    import datetime

    cutoff = timezone.now() - datetime.timedelta(minutes=10)
    pending_tickets = Ticket.objects.filter(
        status=Ticket.STATUS_ISSUED,
        email_sent_at__isnull=True,
        order__status=Order.STATUS_PAID,
        created_at__lt=cutoff,
    ).values_list("id", flat=True)

    for ticket_id in pending_tickets:
        send_ticket_email.delay(str(ticket_id))
