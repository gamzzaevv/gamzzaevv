from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import DocumentPage


@admin.register(DocumentPage)
class DocumentPageAdmin(ModelAdmin):
    list_display = ["slug", "title", "version", "updated_at_display", "is_published"]
    list_filter = ["is_published"]
    readonly_fields = ["created_at", "updated_at"]
