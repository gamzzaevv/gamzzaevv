from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import EmailLog


@admin.register(EmailLog)
class EmailLogAdmin(ModelAdmin):
    list_display = ["recipient", "subject", "status", "retry_count", "sent_at", "created_at"]
    list_filter = ["status", "template_name"]
    search_fields = ["recipient", "subject"]
    readonly_fields = ["recipient", "subject", "template_name", "error", "sent_at", "created_at"]
