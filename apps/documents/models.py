from django.db import models
from apps.core.models import TimestampedModel


class DocumentPage(TimestampedModel):
    """Legal documents managed via admin."""
    SLUG_CHOICES = [
        ("offer", "Публичная оферта"),
        ("privacy", "Политика конфиденциальности"),
        ("consent", "Согласие на обработку ПД"),
        ("refund", "Правила возврата"),
        ("legal", "Реквизиты"),
        ("cookies", "Политика cookies"),
        ("terms", "Пользовательское соглашение"),
        ("delivery", "Доставка и оплата"),
    ]

    slug = models.SlugField("Slug", unique=True, choices=SLUG_CHOICES)
    title = models.CharField("Заголовок", max_length=255)
    content = models.TextField("Содержание (HTML/Markdown)")
    version = models.CharField("Версия", max_length=20, default="1.0")
    updated_at_display = models.DateField("Дата актуализации")
    is_published = models.BooleanField("Опубликован", default=True)

    class Meta:
        verbose_name = "Документ"
        verbose_name_plural = "Документы"

    def __str__(self):
        return self.title
