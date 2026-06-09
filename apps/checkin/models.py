from django.db import models
from apps.core.models import TimestampedModel
from apps.orders.models import Ticket


class CheckInLog(TimestampedModel):
    """Every scan attempt is logged, regardless of outcome."""
    RESULT_VALID = "valid"
    RESULT_USED = "used"
    RESULT_INVALID = "invalid"
    RESULT_CANCELED = "canceled"
    RESULT_EXPIRED = "expired"

    RESULTS = [
        (RESULT_VALID, "✓ Действителен"),
        (RESULT_USED, "Уже использован"),
        (RESULT_INVALID, "Недействителен"),
        (RESULT_CANCELED, "Отменён"),
        (RESULT_EXPIRED, "Истёк"),
    ]

    ticket = models.ForeignKey(
        Ticket, on_delete=models.SET_NULL, null=True, blank=True, related_name="checkin_logs"
    )
    token_scanned = models.CharField("Токен", max_length=200)
    result = models.CharField("Результат", max_length=20, choices=RESULTS, db_index=True)
    scanned_by = models.CharField("Сканировал", max_length=100, blank=True)
    ip_address = models.GenericIPAddressField("IP", null=True)
    device_info = models.CharField("Устройство", max_length=255, blank=True)

    class Meta:
        verbose_name = "Лог прохода"
        verbose_name_plural = "Журнал проходов"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.result} — {self.token_scanned[:16]}..."
