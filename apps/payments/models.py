from django.db import models
from apps.core.models import TimestampedModel
from apps.orders.models import Order


class Payment(TimestampedModel):
    STATUS_PENDING = "pending"
    STATUS_WAITING = "waiting_for_capture"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_CANCELED = "canceled"
    STATUS_REFUNDED = "refunded"

    STATUSES = [
        (STATUS_PENDING, "Ожидает"),
        (STATUS_WAITING, "Ожидает захвата"),
        (STATUS_SUCCEEDED, "Успешен"),
        (STATUS_CANCELED, "Отменён"),
        (STATUS_REFUNDED, "Возвращён"),
    ]

    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="payment")
    yookassa_payment_id = models.CharField(
        "YooKassa ID", max_length=100, unique=True, null=True, blank=True, db_index=True
    )
    amount = models.DecimalField("Сумма", max_digits=10, decimal_places=2)
    currency = models.CharField("Валюта", max_length=3, default="RUB")
    status = models.CharField("Статус", max_length=30, choices=STATUSES, default=STATUS_PENDING, db_index=True)
    confirmation_url = models.URLField("URL подтверждения", blank=True)
    paid_at = models.DateTimeField("Оплачено", null=True, blank=True)
    refunded_at = models.DateTimeField("Возвращено", null=True, blank=True)
    refund_amount = models.DecimalField("Сумма возврата", max_digits=10, decimal_places=2, default=0)
    raw_response = models.JSONField("Ответ YooKassa", default=dict)

    class Meta:
        verbose_name = "Платёж"
        verbose_name_plural = "Платежи"

    def __str__(self):
        return f"Payment {self.yookassa_payment_id} ({self.status})"


class WebhookEvent(TimestampedModel):
    """Every incoming YooKassa webhook is stored for idempotency & audit."""
    STATUS_RECEIVED = "received"
    STATUS_PROCESSED = "processed"
    STATUS_FAILED = "failed"
    STATUS_SKIPPED = "skipped"

    STATUSES = [
        (STATUS_RECEIVED, "Получен"),
        (STATUS_PROCESSED, "Обработан"),
        (STATUS_FAILED, "Ошибка"),
        (STATUS_SKIPPED, "Пропущен"),
    ]

    event_id = models.CharField("YK Event ID", max_length=100, unique=True, db_index=True)
    event_type = models.CharField("Тип события", max_length=100, db_index=True)
    payment_id = models.CharField("YK Payment ID", max_length=100, db_index=True, blank=True)
    raw_body = models.JSONField("Тело")
    status = models.CharField("Статус", max_length=20, choices=STATUSES, default=STATUS_RECEIVED)
    error = models.TextField("Ошибка", blank=True)
    ip_address = models.GenericIPAddressField("IP отправителя", null=True)

    class Meta:
        verbose_name = "Webhook-событие"
        verbose_name_plural = "Webhook-события"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} / {self.payment_id}"
