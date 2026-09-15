from decimal import Decimal

from django.test import TestCase

from apps.reservations.services import create_reservation
from apps.testing import GUEST, days, make_room_type, make_rooms

from .models import Invoice
from .services import build_invoice, mark_paid


class InvoiceTests(TestCase):
    def setUp(self):
        room_type = make_room_type()
        make_rooms(room_type, 1)
        self.reservation = create_reservation(room_type=room_type, check_in=days(0), check_out=days(3), **GUEST)

    def test_totals_and_tax(self):
        invoice = build_invoice(self.reservation)
        self.assertRegex(invoice.number, r"^INV-\d{4}-\d{5}$")
        self.assertEqual(invoice.subtotal, Decimal("300.00"))
        invoice.tax_rate = Decimal("12.5")
        self.assertEqual(invoice.tax, Decimal("37.50"))
        self.assertEqual(invoice.total, Decimal("337.50"))

    def test_building_twice_returns_the_same_invoice(self):
        first = build_invoice(self.reservation)
        self.assertEqual(build_invoice(self.reservation).pk, first.pk)
        self.assertEqual(first.lines.count(), 1)

    def test_mark_paid(self):
        invoice = mark_paid(build_invoice(self.reservation), Invoice.PaymentMethod.CARD)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PAID)
        self.assertIsNotNone(invoice.paid_at)
