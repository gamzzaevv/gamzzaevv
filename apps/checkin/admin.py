from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import CheckInLog


@admin.register(CheckInLog)
class CheckInLogAdmin(ModelAdmin):
    list_display = ["result", "ticket", "scanned_by", "ip_address", "created_at"]
    list_filter = ["result"]
    search_fields = ["token_scanned", "scanned_by"]
    readonly_fields = ["ticket", "token_scanned", "result", "scanned_by", "ip_address", "device_info", "created_at"]
