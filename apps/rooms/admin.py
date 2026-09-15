from django.contrib import admin

from .models import Amenity, Room, RoomType

admin.site.register(Amenity)


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "nightly_rate", "capacity", "is_active"]
    prepopulated_fields = {"slug": ["name"]}
    filter_horizontal = ["amenities"]


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ["number", "floor", "room_type", "status"]
    list_filter = ["status", "room_type", "floor"]
