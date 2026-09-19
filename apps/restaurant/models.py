from decimal import Decimal

from django.conf import settings
from django.db import models


class MenuCategory(models.Model):
    name = models.CharField(max_length=60, unique=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "name"]
        verbose_name_plural = "menu categories"

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    category = models.ForeignKey(MenuCategory, on_delete=models.PROTECT, related_name="items")
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to="menu/", blank=True)
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ["category__position", "name"]

    def __str__(self):
        return self.name


class Order(models.Model):
    class OrderType(models.TextChoices):
        DINE_IN = "dine_in", "Dine-in"
        ROOM_SERVICE = "room_service", "Room service"

    class Status(models.TextChoices):
        PLACED = "placed", "Placed"
        PREPARING = "preparing", "Preparing"
        SERVED = "served", "Served"
        CANCELLED = "cancelled", "Cancelled"

    order_type = models.CharField(max_length=20, choices=OrderType.choices, default=OrderType.DINE_IN)
    table_number = models.CharField(max_length=10, blank=True)
    reservation = models.ForeignKey(
        "reservations.Reservation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        help_text="In-house guest this order is charged to.",
    )
    charge_to_room = models.BooleanField(default=False)
    is_paid = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLACED)
    notes = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk}"

    @property
    def total(self):
        return sum((item.amount for item in self.items.all()), Decimal("0.00"))

    @property
    def location(self):
        if self.order_type == self.OrderType.ROOM_SERVICE and self.reservation and self.reservation.room:
            return str(self.reservation.room)
        return f"Table {self.table_number}" if self.table_number else "—"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT, related_name="+")
    quantity = models.PositiveSmallIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} × {self.menu_item}"

    @property
    def amount(self):
        return self.unit_price * self.quantity
