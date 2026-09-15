from decimal import Decimal

from django.test import TestCase

from apps.billing.models import Invoice
from apps.housekeeping.models import HousekeepingTask
from apps.restaurant.models import MenuCategory, MenuItem, Order, OrderItem
from apps.rooms.models import Room
from apps.testing import GUEST, days, make_room_type, make_rooms

from . import services
from .models import Reservation


class AvailabilityTests(TestCase):
    def setUp(self):
        self.room_type = make_room_type()
        make_rooms(self.room_type, 2)

    def book(self, start, end, **extra):
        return services.create_reservation(
            room_type=self.room_type, check_in=days(start), check_out=days(end), **GUEST, **extra
        )

    def test_back_to_back_stays_do_not_overlap(self):
        self.book(1, 3)
        self.assertEqual(services.available_count(self.room_type, days(1), days(4)), 1)
        self.assertEqual(services.available_count(self.room_type, days(3), days(5)), 2)

    def test_uses_busiest_night_rather_than_total_overlaps(self):
        self.book(1, 2)
        self.book(3, 4)
        self.assertEqual(services.available_count(self.room_type, days(1), days(4)), 1)

    def test_rejects_overbooking(self):
        self.book(1, 3)
        self.book(2, 4)
        with self.assertRaisesMessage(services.BookingError, "fully booked"):
            self.book(2, 3)

    def test_cancelled_bookings_release_inventory(self):
        first = self.book(1, 3)
        self.book(1, 3)
        services.cancel(first)
        self.assertEqual(services.available_count(self.room_type, days(1), days(3)), 1)

    def test_rooms_under_maintenance_are_not_bookable(self):
        Room.objects.update(status=Room.Status.MAINTENANCE)
        self.assertEqual(services.available_count(self.room_type, days(1), days(2)), 0)

    def test_stay_validation(self):
        for start, end, message in [(-1, 1, "past"), (2, 2, "after check-in"), (1, 40, "limited")]:
            with self.subTest(message=message), self.assertRaisesMessage(services.BookingError, message):
                self.book(start, end)

    def test_party_must_fit_room(self):
        with self.assertRaisesMessage(services.BookingError, "sleeps up to 2"):
            self.book(1, 2, adults=2, children=1)

    def test_reference_format_and_rate_snapshot(self):
        reservation = self.book(1, 3)
        self.assertRegex(reservation.reference, r"^GA[A-Z2-9]{6}$")
        self.room_type.nightly_rate = Decimal("999.00")
        self.room_type.save()
        reservation.refresh_from_db()
        self.assertEqual(reservation.room_total, Decimal("200.00"))


class StayLifecycleTests(TestCase):
    def setUp(self):
        self.room_type = make_room_type()
        self.room, self.other_room = make_rooms(self.room_type, 2)
        self.reservation = services.create_reservation(
            room_type=self.room_type, check_in=days(0), check_out=days(2), **GUEST
        )

    def test_check_in_to_check_out(self):
        services.check_in(self.reservation, self.room)
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, Room.Status.OCCUPIED)

        category = MenuCategory.objects.create(name="Mains")
        soup = MenuItem.objects.create(category=category, name="Soup", price=Decimal("8.50"))
        order = Order.objects.create(reservation=self.reservation, charge_to_room=True,
                                     order_type=Order.OrderType.ROOM_SERVICE)
        OrderItem.objects.create(order=order, menu_item=soup, quantity=2, unit_price=soup.price)

        invoice = services.check_out(self.reservation)
        self.reservation.refresh_from_db()
        self.room.refresh_from_db()
        self.assertEqual(self.reservation.status, Reservation.Status.CHECKED_OUT)
        self.assertEqual(self.room.status, Room.Status.CLEANING)
        self.assertTrue(HousekeepingTask.objects.filter(room=self.room, status="pending").exists())
        self.assertEqual(invoice.subtotal, Decimal("217.00"))  # 2 nights × 100 + 2 × 8.50
        self.assertEqual(invoice.status, Invoice.Status.UNPAID)

    def test_room_assigned_to_overlapping_stay_is_not_offered(self):
        other = services.create_reservation(room_type=self.room_type, check_in=days(0), check_out=days(1), **GUEST)
        services.check_in(other, self.room)
        Room.objects.filter(pk=self.room.pk).update(status=Room.Status.AVAILABLE)
        self.assertNotIn(self.room, services.assignable_rooms(self.reservation))
        with self.assertRaises(services.BookingError):
            services.check_in(self.reservation, self.room)

    def test_cannot_check_in_early_or_twice(self):
        future = services.create_reservation(room_type=self.room_type, check_in=days(5), check_out=days(6), **GUEST)
        with self.assertRaises(services.BookingError):
            services.check_in(future, self.other_room)
        services.check_in(self.reservation, self.room)
        with self.assertRaises(services.BookingError):
            services.check_in(self.reservation, self.other_room)

    def test_guest_cannot_cancel_after_arrival_but_staff_can_mark_no_show(self):
        Reservation.objects.filter(pk=self.reservation.pk).update(check_in=days(-1), check_out=days(1))
        self.reservation.refresh_from_db()
        with self.assertRaises(services.BookingError):
            services.cancel(self.reservation)
        services.mark_no_show(self.reservation)
        self.assertEqual(self.reservation.status, Reservation.Status.NO_SHOW)
