from django.db import transaction
from django.utils import timezone

from apps.restaurant.models import Order

from .models import Invoice, InvoiceLine


def build_invoice(reservation):
    """Create the stay invoice: room nights plus restaurant orders charged to the room."""
    invoice, created = Invoice.objects.get_or_create(reservation=reservation)
    if not created:
        return invoice
    nights = reservation.nights
    InvoiceLine.objects.create(
        invoice=invoice,
        description=f"{reservation.room_type.name} – {nights} night{'s' if nights != 1 else ''}",
        quantity=nights,
        unit_price=reservation.nightly_rate,
    )
    orders = reservation.orders.filter(charge_to_room=True).exclude(status=Order.Status.CANCELLED)
    for order in orders.prefetch_related("items"):
        InvoiceLine.objects.create(
            invoice=invoice,
            description=f"{order.get_order_type_display()} – order #{order.pk}",
            quantity=1,
            unit_price=order.total,
        )
    return invoice


def mark_paid(invoice, payment_method):
    with transaction.atomic():
        invoice.status = Invoice.Status.PAID
        invoice.payment_method = payment_method
        invoice.paid_at = timezone.now()
        invoice.save(update_fields=["status", "payment_method", "paid_at"])
        invoice.reservation.orders.filter(charge_to_room=True).update(is_paid=True)
    return invoice
