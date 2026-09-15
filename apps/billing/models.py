from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse

CENT = Decimal("0.01")


class Invoice(models.Model):
    class Status(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PAID = "paid", "Paid"

    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Cash"
        CARD = "card", "Card"
        OTHER = "other", "Other"

    reservation = models.OneToOneField(
        "reservations.Reservation", on_delete=models.PROTECT, related_name="invoice"
    )
    number = models.CharField(max_length=20, unique=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.UNPAID)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=settings.HOTEL_TAX_RATE)
    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-issued_at"]

    def __str__(self):
        return self.number or f"Invoice #{self.pk}"

    def get_absolute_url(self):
        return reverse("billing:detail", args=[self.pk])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.number:
            self.number = f"INV-{self.issued_at:%Y}-{self.pk:05d}"
            super().save(update_fields=["number"])

    @property
    def subtotal(self):
        return sum((line.amount for line in self.lines.all()), Decimal("0.00"))

    @property
    def tax(self):
        return (self.subtotal * self.tax_rate / 100).quantize(CENT, ROUND_HALF_UP)

    @property
    def total(self):
        return self.subtotal + self.tax


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    description = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["pk"]

    def __str__(self):
        return self.description

    @property
    def amount(self):
        return self.unit_price * self.quantity
