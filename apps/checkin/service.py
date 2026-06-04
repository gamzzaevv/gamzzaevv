"""Ticket validation logic for the check-in module."""
import logging
from django.db import transaction
from apps.checkin.models import CheckInLog
from apps.orders.models import Ticket

logger = logging.getLogger(__name__)

_RESULT_MAP = {
    Ticket.STATUS_ISSUED: CheckInLog.RESULT_VALID,
    Ticket.STATUS_USED: CheckInLog.RESULT_USED,
    Ticket.STATUS_CANCELED: CheckInLog.RESULT_CANCELED,
    Ticket.STATUS_EXPIRED: CheckInLog.RESULT_EXPIRED,
}

STATUS_MESSAGES = {
    CheckInLog.RESULT_VALID: "✓ Билет действителен — добро пожаловать!",
    CheckInLog.RESULT_USED: "✗ Билет уже был использован",
    CheckInLog.RESULT_INVALID: "✗ Билет не найден",
    CheckInLog.RESULT_CANCELED: "✗ Билет отменён",
    CheckInLog.RESULT_EXPIRED: "✗ Билет истёк",
}


def validate_ticket(
    token: str,
    scanned_by: str = "",
    ip_address: str | None = None,
    device_info: str = "",
) -> dict:
    """
    Validate a ticket by token.
    Returns dict with result, message, and ticket data.
    Atomically marks valid ticket as 'used'.
    """
    with transaction.atomic():
        try:
            ticket = Ticket.objects.select_for_update().select_related(
                "order__customer", "order__ticket_type__event"
            ).get(token=token)
        except Ticket.DoesNotExist:
            _log(None, token, CheckInLog.RESULT_INVALID, scanned_by, ip_address, device_info)
            return _response(CheckInLog.RESULT_INVALID, token=token)

        result = _RESULT_MAP.get(ticket.status, CheckInLog.RESULT_INVALID)

        if result == CheckInLog.RESULT_VALID:
            ticket.status = Ticket.STATUS_USED
            ticket.save(update_fields=["status", "updated_at"])

        _log(ticket, token, result, scanned_by, ip_address, device_info)

    logger.info(
        "checkin_scan",
        extra={"token": token[:16], "result": result, "scanned_by": scanned_by},
    )
    return _response(result, ticket=ticket)


def _log(ticket, token, result, scanned_by, ip, device):
    CheckInLog.objects.create(
        ticket=ticket,
        token_scanned=token,
        result=result,
        scanned_by=scanned_by,
        ip_address=ip,
        device_info=device,
    )


def _response(result: str, ticket: Ticket | None = None, token: str = "") -> dict:
    data = {
        "result": result,
        "message": STATUS_MESSAGES[result],
        "is_valid": result == CheckInLog.RESULT_VALID,
    }
    if ticket:
        order = ticket.order
        event = order.ticket_type.event
        data["ticket"] = {
            "number": ticket.ticket_number,
            "holder": order.customer.full_name,
            "ticket_type": order.ticket_type.name,
            "event": event.title,
            "event_date": event.starts_at.strftime("%d.%m.%Y %H:%M"),
        }
    return data
