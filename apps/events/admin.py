from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import Event, TicketType, PromoCode


class TicketTypeInline(TabularInline):
    model = TicketType
    extra = 1
    fields = ["name", "price", "total_quantity", "sold_quantity", "reserved_quantity", "sort_order", "is_visible"]
    readonly_fields = ["sold_quantity", "reserved_quantity"]


@admin.register(Event)
class EventAdmin(ModelAdmin):
    list_display = ["title", "starts_at", "venue_city", "is_published", "is_active"]
    list_filter = ["is_published", "is_active", "venue_city"]
    search_fields = ["title", "venue_name"]
    prepopulated_fields = {"slug": ("title",)}
    inlines = [TicketTypeInline]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(PromoCode)
class PromoCodeAdmin(ModelAdmin):
    list_display = ["code", "discount_type", "discount_value", "used_count", "max_uses", "is_active", "valid_until"]
    list_filter = ["discount_type", "is_active"]
    search_fields = ["code"]
    readonly_fields = ["used_count", "created_at"]
