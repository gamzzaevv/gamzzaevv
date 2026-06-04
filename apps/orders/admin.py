import csv
from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from unfold.admin import ModelAdmin
from .models import Customer, Order, Ticket, ConsentLog


def export_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = 'attachment; filename="orders_export.csv"'
    writer = csv.writer(response)
    writer.writerow(["Номер заказа", "Покупатель", "Email", "Тип", "Сумма", "Статус", "Создан"])
    for order in queryset.select_related("customer", "ticket_type"):
        writer.writerow([
            order.order_number,
            order.customer.full_name,
            order.customer.email,
            order.ticket_type.name,
            order.total_amount,
            order.get_status_display(),
            order.created_at.strftime("%d.%m.%Y %H:%M"),
        ])
    return response

export_csv.short_description = "Экспорт в CSV"


@admin.register(Customer)
class CustomerAdmin(ModelAdmin):
    list_display = ["full_name", "email", "phone", "consent_given_at", "created_at"]
    search_fields = ["email", "first_name", "last_name"]
    readonly_fields = ["consent_given_at", "consent_ip", "offer_accepted_at", "created_at"]


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ["order_number", "customer", "ticket_type", "total_amount", "status", "created_at"]
    list_filter = ["status", "ticket_type__event", "created_at"]
    search_fields = ["order_number", "customer__email", "customer__last_name"]
    readonly_fields = ["order_number", "customer", "ticket_type", "unit_price",
                       "discount_amount", "total_amount", "ip_address", "created_at", "updated_at"]
    actions = [export_csv]

    def resend_email(self, request, queryset):
        from tasks.email_tasks import send_ticket_email
        for order in queryset.filter(status=Order.STATUS_PAID):
            for ticket in order.tickets.all():
                send_ticket_email.delay(str(ticket.id))
        self.message_user(request, "Email поставлен в очередь")
    resend_email.short_description = "Переотправить email"


@admin.register(Ticket)
class TicketAdmin(ModelAdmin):
    list_display = ["ticket_number", "order", "status", "email_sent_at", "created_at"]
    list_filter = ["status"]
    search_fields = ["ticket_number", "verify_code", "order__order_number"]
    readonly_fields = ["ticket_number", "token", "verify_code", "pdf_file", "created_at", "updated_at"]

    def cancel_ticket(self, request, queryset):
        queryset.filter(status=Ticket.STATUS_ISSUED).update(status=Ticket.STATUS_CANCELED)
        self.message_user(request, "Билеты отменены")
    cancel_ticket.short_description = "Отменить билеты"

    def regenerate_pdf(self, request, queryset):
        from apps.orders.pdf_generator import generate_pdf
        for ticket in queryset:
            generate_pdf(ticket)
        self.message_user(request, "PDF перегенерированы")
    regenerate_pdf.short_description = "Перегенерировать PDF"

    actions = ["cancel_ticket", "regenerate_pdf"]
