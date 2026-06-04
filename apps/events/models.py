from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from apps.core.models import TimestampedModel


class Event(TimestampedModel):
    """A single sports event / fight night."""
    title = models.CharField("Название", max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField("Описание", blank=True)
    short_description = models.CharField("Краткое описание", max_length=500, blank=True)

    # Timing
    starts_at = models.DateTimeField("Начало")
    doors_open_at = models.DateTimeField("Открытие дверей", null=True, blank=True)

    # Venue
    venue_name = models.CharField("Площадка", max_length=255)
    venue_address = models.TextField("Адрес")
    venue_city = models.CharField("Город", max_length=100, default="Москва")
    venue_map_url = models.URLField("Ссылка на карту", blank=True)

    # Media
    poster = models.ImageField("Постер", upload_to="events/posters/", null=True, blank=True)
    banner = models.ImageField("Баннер", upload_to="events/banners/", null=True, blank=True)

    # State
    is_published = models.BooleanField("Опубликовано", default=False, db_index=True)
    is_active = models.BooleanField("Активно", default=True)

    class Meta:
        verbose_name = "Мероприятие"
        verbose_name_plural = "Мероприятия"
        ordering = ["-starts_at"]

    def __str__(self):
        return self.title

    @property
    def is_upcoming(self) -> bool:
        return self.starts_at > timezone.now()


class TicketType(TimestampedModel):
    """Category of ticket for an event (Standard / VIP / Front Row)."""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="ticket_types")
    name = models.CharField("Название", max_length=100)
    description = models.TextField("Описание", blank=True)
    price = models.DecimalField(
        "Цена (руб.)", max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))]
    )
    total_quantity = models.PositiveIntegerField("Всего билетов")
    sold_quantity = models.PositiveIntegerField("Продано", default=0)
    reserved_quantity = models.PositiveIntegerField("Зарезервировано", default=0)
    sort_order = models.PositiveSmallIntegerField("Порядок", default=0)
    is_visible = models.BooleanField("Отображать", default=True)

    class Meta:
        verbose_name = "Тип билета"
        verbose_name_plural = "Типы билетов"
        ordering = ["sort_order", "price"]
        unique_together = [["event", "name"]]

    def __str__(self):
        return f"{self.event} — {self.name}"

    @property
    def available_quantity(self) -> int:
        return self.total_quantity - self.sold_quantity - self.reserved_quantity

    @property
    def is_sold_out(self) -> bool:
        return self.available_quantity <= 0


class PromoCode(TimestampedModel):
    """Discount promo codes."""
    DISCOUNT_FIXED = "fixed"
    DISCOUNT_PERCENT = "percent"
    DISCOUNT_TYPES = [
        (DISCOUNT_FIXED, "Фиксированная сумма"),
        (DISCOUNT_PERCENT, "Процент"),
    ]

    code = models.CharField("Код", max_length=50, unique=True, db_index=True)
    discount_type = models.CharField("Тип скидки", max_length=10, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField("Размер скидки", max_digits=10, decimal_places=2)
    max_uses = models.PositiveIntegerField("Макс. использований", null=True, blank=True)
    used_count = models.PositiveIntegerField("Использовано", default=0)
    valid_from = models.DateTimeField("Действует с", null=True, blank=True)
    valid_until = models.DateTimeField("Действует до", null=True, blank=True)
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, null=True, blank=True,
        help_text="Если пусто — применяется ко всем событиям"
    )
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        verbose_name = "Промокод"
        verbose_name_plural = "Промокоды"

    def __str__(self):
        return self.code

    def is_valid(self) -> bool:
        now = timezone.now()
        if not self.is_active:
            return False
        if self.max_uses and self.used_count >= self.max_uses:
            return False
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True

    def apply(self, price: Decimal) -> Decimal:
        if self.discount_type == self.DISCOUNT_FIXED:
            return max(Decimal("0"), price - self.discount_value)
        return max(Decimal("0"), price * (1 - self.discount_value / 100))
