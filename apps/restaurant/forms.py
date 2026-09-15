from django import forms

from apps.reservations.models import Reservation

from .models import MenuCategory, MenuItem, Order


class MenuItemForm(forms.ModelForm):
    class Meta:
        model = MenuItem
        fields = ["category", "name", "description", "price", "is_available"]


class MenuCategoryForm(forms.ModelForm):
    class Meta:
        model = MenuCategory
        fields = ["name", "position"]


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["order_type", "table_number", "reservation", "charge_to_room", "notes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reservation"].queryset = Reservation.objects.filter(
            status=Reservation.Status.CHECKED_IN
        ).select_related("room")
        self.fields["reservation"].label = "In-house guest"
        self.fields["reservation"].label_from_instance = lambda r: f"{r.room} · {r.guest_name}"

    def clean(self):
        cleaned = super().clean()
        order_type = cleaned.get("order_type")
        reservation = cleaned.get("reservation")
        if order_type == Order.OrderType.ROOM_SERVICE and not reservation:
            self.add_error("reservation", "Room service needs an in-house guest.")
        if order_type == Order.OrderType.DINE_IN and not cleaned.get("table_number") and not reservation:
            self.add_error("table_number", "Enter a table number.")
        if cleaned.get("charge_to_room") and not reservation:
            self.add_error("charge_to_room", "Only in-house guests can charge to their room.")
        return cleaned
