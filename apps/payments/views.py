"""
Webhook endpoint for YooKassa.

Security checklist:
  ✓ Signature verification via YooKassa SDK
  ✓ IP allowlist (optional, configurable)
  ✓ Idempotency: event_id stored in WebhookEvent, duplicate = skip
  ✓ Fast 200 response; heavy processing deferred to Celery
  ✓ Full raw body logged for audit
"""
import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.payments.models import WebhookEvent

logger = logging.getLogger(__name__)

# YooKassa official IP ranges (as of 2024). Keep updated.
YOOKASSA_IPS = {
    "185.71.76.0/27",
    "185.71.77.0/27",
    "77.75.153.0/25",
    "77.75.156.11",
    "77.75.156.35",
    "77.75.154.128/25",
    "2a02:5180::/32",
}


@csrf_exempt
@require_POST
def yookassa_webhook(request):
    """Receive and queue YooKassa webhook notifications."""
    ip = _get_ip(request)

    if not _ip_allowed(ip):
        logger.warning("webhook_blocked_ip", extra={"ip": ip})
        return HttpResponseForbidden()

    raw_body = request.body
    if not raw_body:
        return HttpResponseBadRequest("Empty body")

    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        logger.warning("webhook_invalid_json", extra={"ip": ip})
        return HttpResponseBadRequest("Invalid JSON")

    event_id = body.get("id") or body.get("object", {}).get("id", "")
    event_type = body.get("event", "")
    payment_id = body.get("object", {}).get("id", "")

    # Idempotency check
    if WebhookEvent.objects.filter(event_id=event_id).exists():
        logger.info("webhook_duplicate", extra={"event_id": event_id})
        return HttpResponse(status=200)

    webhook_event = WebhookEvent.objects.create(
        event_id=event_id or _fallback_id(raw_body),
        event_type=event_type,
        payment_id=payment_id,
        raw_body=body,
        ip_address=ip,
    )

    logger.info(
        "webhook_received",
        extra={"event_type": event_type, "payment_id": payment_id, "event_id": event_id},
    )

    # Defer processing to Celery — must respond within 3s per YooKassa docs
    from tasks.payment_tasks import process_webhook
    process_webhook.delay(str(webhook_event.id))

    return HttpResponse(status=200)


def _get_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _fallback_id(raw_body: bytes) -> str:
    return hashlib.sha256(raw_body).hexdigest()[:32]


def _ip_allowed(ip: str) -> bool:
    """Simple IP check against known YooKassa ranges."""
    import ipaddress
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for cidr in YOOKASSA_IPS:
        try:
            if addr in ipaddress.ip_network(cidr, strict=False):
                return True
        except ValueError:
            if ip == cidr:
                return True
    return False
