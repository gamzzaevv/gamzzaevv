import hashlib
import secrets
import uuid
from django.db import models, transaction
from django.utils import timezone
from apps.core.models import TimestampedModel
from apps.events.models import TicketType, PromoCode


class Customer(TimestampedModel):
    """Person who purchases a ticket (not a site user)."""
    email = models.EmailField("Email", db_index=True)
    first_name = models.CharField("Имя", max_length=100)
    last_name = models.CharField("Фамилия", max_length=100)
    patronymic = models.CharField("Отчество", max_length=100, blank=True)
    phone = models.CharField("Телефон", max_length=20, blank=True)

    # GDPR/152-FZ consent
    consent_given_at = models.DateTimeField("Согласие дано", null=True)
    consent_ip = models.GenericIPAddressField("IP согласия", null=True)
    offer_accepted_at = models.DateTimeField("Оферта принята", null=True)

    class Meta:
        verbose_name = "Покупатель"
        verbose_name_plural = "Покупатели"

    def __str__(self):
        return f"{self.last_name} {self.first_name} <{self.email}>"

    @property
    def full_name(self) -> str:
        parts = [self.last_name, self.first_name, self.patronymic]
        return " ".join(p for p in parts if p)


class Order(TimestampedModel):
    """Single purchase session."""
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_CANCELED = "canceled"
    STATUS_REFUNDED = "refunded"
    STATUS_EXPIRED = "expired"

    STATUSES = [
        (STATUS_PENDING, "Ожидает оплаты"),
        (STATUS_PAID, "Оплачен"),
        (STATUS_CANCELED, "Отменён"),
        (STATUS_REFUNDED, "Возвращён"),
        (STATUS_EXPIRED, "Истёк"),
    ]

    order_number = models.CharField("Номер заказа", max_length=20, unique=True, db_index=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="orders")
    ticket_type = models.ForeignKey(TicketType, on_delete=models.PROTECT, related_name="orders")
    promo_code = models.ForeignKey(
        PromoCode, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    quantity = models.PositiveSmallIntegerField("Количество", default=1)

    # Pricing snapshot
    unit_price = models.DecimalField("Цена за штуку", max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField("Скидка", max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField("Итого", max_digits=10, decimal_places=2)

    status = models.CharField("Статус", max_length=20, choices=STATUSES, default=STATUS_PENDING, db_index=True)
    expires_at = models.DateTimeField("Истекает")  # reservation window

    # Metadata
    ip_address = models.GenericIPAddressField("IP", null=True)
    user_agent = models.TextField("User-Agent", blank=True)
    notes = models.TextField("Заметки", blank=True)

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.order_number}"

    @classmethod
    def generate_order_number(cls) -> str:
        ts = timezone.now().strftime("%Y%m%d")
        rand = secrets.randbelow(100000)
        return f"FN-{ts}-{rand:05d}"

    def is_expired(self) -> bool:
        return self.status == self.STATUS_PENDING and timezone.now() > self.expires_at


class Ticket(TimestampedModel):
    """
    One physical ticket per seat / attendee.
    One Order can produce multiple Tickets (quantity > 1).
    """
    STATUS_ISSUED = "issued"
    STATUS_USED = "used"
    STATUS_CANCELED = "canceled"
    STATUS_EXPIRED = "expired"

    STATUSES = [
        (STATUS_ISSUED, "Выдан"),
        (STATUS_USED, "Использован"),
        (STATUS_CANCELED, "Отменён"),
        (STATUS_EXPIRED, "Истёк"),
    ]

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="tickets")
    ticket_number = models.CharField("Номер билета", max_length=30, unique=True, db_index=True)

    # Immutable token used in QR
    token = models.CharField("Токен", max_length=64, unique=True, db_index=True)
    # Human-readable verification code (printed on ticket)
    verify_code = models.CharField("Код проверки", max_length=12, unique=True)

    status = models.CharField("Статус", max_length=20, choices=STATUSES, default=STATUS_ISSUED, db_index=True)

    # PDF storage
    pdf_file = models.FileField("PDF", upload_to="tickets/pdf/", null=True, blank=True)

    # Email delivery
    email_sent_at = models.DateTimeField("Email отправлен", null=True, blank=True)

    class Meta:
        verbose_name = "Билет"
        verbose_name_plural = "Билеты"
        ordering = ["-created_at"]

    def __str__(self):
        return self.ticket_number

    @classmethod
    def generate_token(cls) -> str:
        return secrets.token_urlsafe(48)

    @classmethod
    def generate_verify_code(cls) -> str:
        return secrets.token_hex(6).upper()  # e.g. A3F9B2C1D0E5

    def get_qr_data(self) -> str:
        from django.conf import settings
        return f"{settings.SITE_URL}/checkin/verify/{self.token}/"


class ConsentLog(TimestampedModel):
    """Audit trail for personal data consents (152-FZ)."""
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="consent_logs")
    consent_type = models.CharField("Тип согласия", max_length=50)
    document_version = models.CharField("Версия документа", max_length=20)
    ip_address = models.GenericIPAddressField("IP")
    user_agent = models.TextField("User-Agent")

    class Meta:
        verbose_name = "Журнал согласий"
        verbose_name_plural = "Журнал согласий"
