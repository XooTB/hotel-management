from django.contrib import admin

from .models import Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ["reference", "guest_name", "room_type", "room", "check_in", "check_out", "status"]
    list_filter = ["status", "source", "room_type"]
    search_fields = ["reference", "guest_name", "guest_email"]
    date_hierarchy = "check_in"
