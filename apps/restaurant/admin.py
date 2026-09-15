from django.contrib import admin

from .models import MenuCategory, MenuItem, Order, OrderItem

admin.site.register(MenuCategory)


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "price", "is_available"]
    list_filter = ["category", "is_available"]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["pk", "order_type", "status", "charge_to_room", "is_paid", "created_at"]
    list_filter = ["status", "order_type"]
    inlines = [OrderItemInline]
