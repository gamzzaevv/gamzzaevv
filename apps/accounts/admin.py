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
