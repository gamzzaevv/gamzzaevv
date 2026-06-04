"""Email sending service with audit logging."""
import logging
from email.mime.application import MIMEApplication

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from apps.notifications.models import EmailLog
from apps.orders.models import Ticket

logger = logging.getLogger(__name__)


def send_ticket_confirmation(ticket: Ticket) -> None:
    """Send branded ticket email with PDF attachment to buyer + admin notification."""
    order = ticket.order
    customer = order.customer
    event = order.ticket_type.event

    ctx = {
        "ticket": ticket,
        "order": order,
        "customer": customer,
        "event": event,
        "site_name": settings.SITE_NAME,
        "site_url": settings.SITE_URL,
        "verify_url": f"{settings.SITE_URL}/checkin/verify/{ticket.token}/",
    }

    subject = f"Ваш билет — {event.title}"
    html_body = render_to_string("emails/ticket_confirmation.html", ctx)
    text_body = render_to_string("emails/ticket_confirmation.txt", ctx)

    log = EmailLog.objects.create(
        ticket=ticket,
        recipient=customer.email,
        subject=subject,
        template_name="emails/ticket_confirmation",
    )

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[customer.email],
            reply_to=[settings.ADMIN_EMAIL],
        )
        msg.attach_alternative(html_body, "text/html")

        # Attach PDF if generated
        if ticket.pdf_file:
            with ticket.pdf_file.open("rb") as f:
                pdf_data = f.read()
            msg.attach(
                filename=f"ticket_{ticket.ticket_number}.pdf",
                content=pdf_data,
                mimetype="application/pdf",
            )

        msg.send()

        log.status = EmailLog.STATUS_SENT
        log.sent_at = timezone.now()
        log.save(update_fields=["status", "sent_at", "updated_at"])

        logger.info("email_sent", extra={"recipient": customer.email, "ticket": ticket.ticket_number})

    except Exception as exc:
        log.status = EmailLog.STATUS_FAILED
        log.error = str(exc)
        log.retry_count += 1
        log.save(update_fields=["status", "error", "retry_count", "updated_at"])
        logger.exception("email_failed", extra={"recipient": customer.email})
        raise

    # Admin notification (best-effort, non-blocking)
    try:
        _send_admin_notification(ticket, ctx)
    except Exception:
        logger.warning("admin_notification_failed", extra={"ticket": ticket.ticket_number})


def _send_admin_notification(ticket: Ticket, ctx: dict) -> None:
    subject = f"[Новый заказ] {ticket.order.order_number} — {ctx['event'].title}"
    body = render_to_string("emails/admin_new_order.txt", ctx)
    msg = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.ADMIN_EMAIL],
    )
    msg.send()
