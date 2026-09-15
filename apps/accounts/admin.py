from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class StaffUserAdmin(UserAdmin):
    list_display = ["username", "get_full_name", "email", "role", "is_active"]
    list_filter = ["role", "is_active", "is_superuser"]
    fieldsets = UserAdmin.fieldsets + (("Hotel", {"fields": ("role", "phone")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Hotel", {"fields": ("role", "phone")}),)
