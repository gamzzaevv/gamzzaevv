from django.db import models
from apps.core.models import TimestampedModel
from apps.orders.models import Ticket


class EmailLog(TimestampedModel):
    STATUS_QUEUED = "queued"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"

    STATUSES = [
        (STATUS_QUEUED, "В очереди"),
        (STATUS_SENT, "Отправлен"),
        (STATUS_FAILED, "Ошибка"),
    ]

    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="email_logs", null=True, blank=True
    )
    recipient = models.EmailField("Получатель")
    subject = models.CharField("Тема", max_length=255)
    template_name = models.CharField("Шаблон", max_length=100)
    status = models.CharField("Статус", max_length=20, choices=STATUSES, default=STATUS_QUEUED)
    error = models.TextField("Ошибка", blank=True)
    sent_at = models.DateTimeField("Отправлен", null=True, blank=True)
    retry_count = models.PositiveSmallIntegerField("Попыток", default=0)

    class Meta:
        verbose_name = "Лог email"
        verbose_name_plural = "Логи email"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.recipient} — {self.subject} [{self.status}]"
