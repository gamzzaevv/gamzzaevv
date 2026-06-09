from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Payment, WebhookEvent


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = ["order", "yookassa_payment_id", "amount", "status", "paid_at", "created_at"]
    list_filter = ["status", "currency"]
    search_fields = ["yookassa_payment_id", "order__order_number"]
    readonly_fields = ["yookassa_payment_id", "amount", "currency", "confirmation_url",
                       "paid_at", "refunded_at", "raw_response", "created_at", "updated_at"]

    def issue_refund(self, request, queryset):
        from apps.payments.service import create_refund
        for payment in queryset.filter(status=Payment.STATUS_SUCCEEDED):
            create_refund(payment)
        self.message_user(request, "Запросы на возврат отправлены")
    issue_refund.short_description = "Оформить возврат"
    actions = ["issue_refund"]


@admin.register(WebhookEvent)
class WebhookEventAdmin(ModelAdmin):
    list_display = ["event_type", "payment_id", "status", "ip_address", "created_at"]
    list_filter = ["status", "event_type"]
    readonly_fields = ["event_id", "event_type", "payment_id", "raw_body",
                       "ip_address", "error", "created_at", "updated_at"]
