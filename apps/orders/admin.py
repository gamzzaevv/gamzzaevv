import csv

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import FileResponse, Http404, HttpResponse
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html

from unfold.admin import ModelAdmin, TabularInline

from .models import Customer, Order, Ticket, ConsentLog


# ─── Цветной значок статуса ──────────────────────────────────────────────────
_ORDER_STATUS_COLORS = {
    Order.STATUS_PENDING: ("#92400e", "#fef3c7"),    # ожидает — жёлтый
    Order.STATUS_PAID: ("#166534", "#dcfce7"),       # оплачен — зелёный
    Order.STATUS_CANCELED: ("#991b1b", "#fee2e2"),   # отменён — красный
    Order.STATUS_REFUNDED: ("#1e40af", "#dbeafe"),   # возврат — синий
    Order.STATUS_EXPIRED: ("#6b7280", "#e5e7eb"),    # истёк — серый
}

_TICKET_STATUS_COLORS = {
    Ticket.STATUS_ISSUED: ("#166534", "#dcfce7"),
    Ticket.STATUS_USED: ("#1e40af", "#dbeafe"),
    Ticket.STATUS_CANCELED: ("#991b1b", "#fee2e2"),
    Ticket.STATUS_EXPIRED: ("#6b7280", "#e5e7eb"),
}


def _badge(text, colors):
    fg, bg = colors
    return format_html(
        '<span style="background:{};color:{};padding:3px 10px;border-radius:99px;'
        'font-weight:600;font-size:12px;white-space:nowrap">{}</span>',
        bg, fg, text,
    )


@admin.display(description="PDF")
def pdf_link(obj):
    url = reverse("admin:orders_ticket_download_pdf", args=[obj.pk])
    return format_html('<a href="{}" target="_blank">📄 Скачать / посмотреть</a>', url)


# ─── Экспорт заказов в Excel/CSV ─────────────────────────────────────────────
@admin.action(description="📥 Скачать выбранные заказы (Excel/CSV)")
def export_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = 'attachment; filename="zakazy.csv"'
    writer = csv.writer(response, delimiter=";")
    writer.writerow(["Номер заказа", "Покупатель", "Email", "Телефон",
                     "День", "Сумма", "Статус", "Дата покупки"])
    for order in queryset.select_related("customer", "ticket_type", "ticket_type__event"):
        writer.writerow([
            order.order_number,
            order.customer.full_name,
            order.customer.email,
            order.customer.phone,
            order.ticket_type.event.title,
            order.total_amount,
            order.get_status_display(),
            order.created_at.strftime("%d.%m.%Y %H:%M"),
        ])
    return response


# ─── Билеты внутри заказа ────────────────────────────────────────────────────
class TicketInline(TabularInline):
    model = Ticket
    extra = 0
    can_delete = False
    tab = True
    verbose_name_plural = "Билеты в этом заказе"
    fields = ["ticket_number", "status_badge", "verify_code", pdf_link, "email_sent_at"]
    readonly_fields = ["ticket_number", "status_badge", "verify_code", pdf_link, "email_sent_at"]

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="Статус")
    def status_badge(self, obj):
        return _badge(obj.get_status_display(),
                      _TICKET_STATUS_COLORS.get(obj.status, ("#374151", "#e5e7eb")))


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ["order_number", "buyer", "buyer_email", "buyer_phone",
                    "event_day", "total_amount", "status_badge", "created_at"]
    list_display_links = ["order_number", "buyer"]
    list_filter = ["status", "ticket_type__event", "created_at"]
    search_fields = ["order_number", "customer__email", "customer__last_name",
                     "customer__first_name", "customer__phone"]
    date_hierarchy = "created_at"
    list_per_page = 30
    list_select_related = ["customer", "ticket_type", "ticket_type__event"]
    inlines = [TicketInline]
    actions = [export_csv, "resend_email"]

    readonly_fields = ["order_number", "customer", "ticket_type", "quantity",
                       "unit_price", "discount_amount", "total_amount",
                       "ip_address", "created_at", "updated_at"]

    def save_model(self, request, obj, form, change):
        """
        Если сотрудник вручную меняет статус заказа на «Оплачен» (например,
        оплата пришла на карту/счёт мимо сайта), сразу выпускаем билеты —
        генерируем PDF и отправляем письмо покупателю, как при обычной онлайн-оплате.
        """
        became_paid = (
            change and "status" in form.changed_data
            and obj.status == Order.STATUS_PAID
        )
        super().save_model(request, obj, form, change)
        if became_paid:
            self._issue_tickets(obj)
            self.message_user(
                request,
                "Заказ отмечен оплаченным — билеты выпущены, письмо с PDF отправлено покупателю."
            )

    @staticmethod
    def _issue_tickets(order):
        from apps.orders.service import create_tickets_for_order
        from tasks.payment_tasks import generate_ticket_pdf

        tt = order.ticket_type
        if tt.reserved_quantity > 0:
            moved = min(order.quantity, tt.reserved_quantity)
            tt.reserved_quantity -= moved
            tt.sold_quantity += moved
            tt.save(update_fields=["reserved_quantity", "sold_quantity", "updated_at"])

        for ticket in create_tickets_for_order(order):
            generate_ticket_pdf.delay(str(ticket.id))

    @admin.display(description="Покупатель", ordering="customer__last_name")
    def buyer(self, obj):
        return obj.customer.full_name

    @admin.display(description="Email")
    def buyer_email(self, obj):
        return obj.customer.email

    @admin.display(description="Телефон")
    def buyer_phone(self, obj):
        return obj.customer.phone or "—"

    @admin.display(description="День", ordering="ticket_type__event__starts_at")
    def event_day(self, obj):
        return obj.ticket_type.event.title

    @admin.display(description="Статус", ordering="status")
    def status_badge(self, obj):
        return _badge(obj.get_status_display(),
                      _ORDER_STATUS_COLORS.get(obj.status, ("#374151", "#e5e7eb")))

    @admin.action(description="✉️ Переотправить билет на почту")
    def resend_email(self, request, queryset):
        from tasks.email_tasks import send_ticket_email
        count = 0
        for order in queryset.filter(status=Order.STATUS_PAID):
            for ticket in order.tickets.all():
                send_ticket_email.delay(str(ticket.id))
                count += 1
        self.message_user(request, f"Поставлено в очередь писем: {count}")


@admin.register(Customer)
class CustomerAdmin(ModelAdmin):
    list_display = ["full_name", "email", "phone", "orders_count", "created_at"]
    search_fields = ["email", "first_name", "last_name", "phone"]
    list_per_page = 30
    readonly_fields = ["consent_given_at", "consent_ip", "offer_accepted_at",
                       "created_at", "updated_at"]

    @admin.display(description="ФИО", ordering="last_name")
    def full_name(self, obj):
        return obj.full_name

    @admin.display(description="Заказов")
    def orders_count(self, obj):
        return obj.orders.count()


@admin.register(Ticket)
class TicketAdmin(ModelAdmin):
    list_display = ["ticket_number", "buyer", "buyer_email", "event_day",
                    "status_badge", pdf_link, "email_sent_at", "created_at"]
    list_display_links = ["ticket_number", "buyer"]
    list_filter = ["status", "order__ticket_type__event"]
    search_fields = ["ticket_number", "verify_code", "order__order_number",
                     "order__customer__email", "order__customer__last_name"]
    list_per_page = 30
    list_select_related = ["order", "order__customer",
                           "order__ticket_type", "order__ticket_type__event"]
    readonly_fields = ["ticket_number", "token", "verify_code", "pdf_file",
                       "created_at", "updated_at"]
    actions = ["send_to_email", "cancel_ticket", "regenerate_pdf"]

    # ── Дополнительные URL: скачивание PDF ───────────────────────────────────
    def get_urls(self):
        custom = [
            path(
                "<path:object_id>/download-pdf/",
                self.admin_site.admin_view(self.download_pdf),
                name="orders_ticket_download_pdf",
            ),
        ]
        return custom + super().get_urls()

    def download_pdf(self, request, object_id):
        from apps.orders.pdf_generator import generate_pdf
        ticket = self.get_object(request, object_id)
        if ticket is None:
            raise Http404("Билет не найден")
        if not ticket.pdf_file:
            generate_pdf(ticket)
            ticket.refresh_from_db()
        # as_attachment=False — открывается прямо в новой вкладке браузера
        # (можно посмотреть билет, а сохранить — через меню браузера).
        return FileResponse(
            ticket.pdf_file.open("rb"),
            as_attachment=False,
            filename=f"bilet_{ticket.ticket_number}.pdf",
        )

    @admin.display(description="Покупатель", ordering="order__customer__last_name")
    def buyer(self, obj):
        return obj.order.customer.full_name

    @admin.display(description="Email")
    def buyer_email(self, obj):
        return obj.order.customer.email

    @admin.display(description="День")
    def event_day(self, obj):
        return obj.order.ticket_type.event.title

    @admin.display(description="Статус", ordering="status")
    def status_badge(self, obj):
        return _badge(obj.get_status_display(),
                      _TICKET_STATUS_COLORS.get(obj.status, ("#374151", "#e5e7eb")))

    # ── Действие: отправить билет на e-mail (с исправлением адреса) ───────────
    @admin.action(description="✉️ Отправить билет на e-mail…")
    def send_to_email(self, request, queryset):
        from apps.notifications.service import send_ticket_to_email

        # Шаг 2: пользователь подтвердил адрес — отправляем
        if "apply" in request.POST:
            email = request.POST.get("recipient_email", "").strip()
            try:
                validate_email(email)
            except ValidationError:
                self.message_user(request, "Некорректный e-mail, попробуйте ещё раз.",
                                  level=messages.ERROR)
            else:
                sent = failed = 0
                for ticket in queryset:
                    try:
                        send_ticket_to_email(ticket, email)
                        sent += 1
                    except Exception:
                        failed += 1
                if sent:
                    self.message_user(request, f"Билет отправлен на {email} (шт.: {sent}).")
                if failed:
                    self.message_user(request, f"Не удалось отправить: {failed}.",
                                      level=messages.ERROR)
                return None  # вернуться к списку

        # Шаг 1: показать форму с адресом (по умолчанию — текущий email покупателя)
        prefill = ""
        if queryset.count() == 1:
            prefill = queryset.first().order.customer.email
        context = {
            **self.admin_site.each_context(request),
            "title": "Отправить билет на e-mail",
            "tickets": queryset,
            "prefill": prefill,
            "selected": list(queryset.values_list("pk", flat=True)),
            "opts": self.model._meta,
        }
        return TemplateResponse(request, "admin/orders/send_ticket_email.html", context)

    @admin.action(description="Отменить выбранные билеты")
    def cancel_ticket(self, request, queryset):
        updated = queryset.filter(status=Ticket.STATUS_ISSUED).update(
            status=Ticket.STATUS_CANCELED
        )
        self.message_user(request, f"Отменено билетов: {updated}")

    @admin.action(description="Перегенерировать PDF")
    def regenerate_pdf(self, request, queryset):
        from apps.orders.pdf_generator import generate_pdf
        for ticket in queryset:
            generate_pdf(ticket)
        self.message_user(request, "PDF перегенерированы")


@admin.register(ConsentLog)
class ConsentLogAdmin(ModelAdmin):
    list_display = ["customer", "consent_type", "document_version", "ip_address", "created_at"]
    search_fields = ["customer__email"]
    readonly_fields = ["customer", "consent_type", "document_version",
                       "ip_address", "user_agent", "created_at"]

    def has_add_permission(self, request):
        return False
