from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from unfold.admin import ModelAdmin
from .models import User


@admin.register(User)
class UserAdmin(ModelAdmin, DjangoUserAdmin):
    list_display = ["email", "username", "is_staff", "is_checker", "is_active"]
    list_filter = ["is_staff", "is_checker", "is_active"]
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Дополнительно", {"fields": ("phone", "is_checker")}),
    )


# ─── Убираем технические разделы из админки ───────────────────────────────────
# Эти модели создаются сторонними библиотеками (фоновые задачи, 2FA, защита от
# подбора пароля и т.п.) и не нужны человеку, который продаёт билеты. Прячем их,
# чтобы меню оставалось простым. Сами функции при этом продолжают работать.
_HIDE_APP_LABELS = {
    "django_celery_beat",     # расписания фоновых задач
    "django_celery_results",  # результаты фоновых задач
    "otp_totp",               # 2FA (TOTP)
    "otp_static",             # 2FA (резервные коды)
    "authtoken",              # API-токены DRF
    "account",                # allauth: email-адреса
    "socialaccount",          # allauth: соцсети
    "mfa",                    # allauth: двухфакторка
    "sites",                  # django.contrib.sites
    "axes",                   # защита от подбора пароля
}

for _model, _model_admin in list(admin.site._registry.items()):
    if _model._meta.app_label in _HIDE_APP_LABELS:
        try:
            admin.site.unregister(_model)
        except admin.sites.NotRegistered:
            pass
