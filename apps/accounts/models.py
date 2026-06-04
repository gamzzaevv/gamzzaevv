import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Extended user — staff/admin only. Customers are separate."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=20, blank=True)
    is_checker = models.BooleanField(default=False, help_text="Can access check-in module")

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.email or self.username
