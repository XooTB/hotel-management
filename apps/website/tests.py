from django.core import mail
from django.test import Client, TestCase
from django.urls import reverse

from apps.reservations.models import Reservation
from apps.testing import GUEST, days, make_room_type, make_rooms


class GuestBookingFlowTests(TestCase):
    def setUp(self):
        self.room_type = make_room_type()
        make_rooms(self.room_type, 1)

    def post_booking(self, client=None):
        data = {"check_in": days(2), "check_out": days(4), "adults": 2, "children": 0, **GUEST}
        return (client or self.client).post(reverse("website:book", args=[self.room_type.slug]), data)

    def test_book_confirm_and_cancel(self):
        response = self.post_booking()
        reservation = Reservation.objects.get()
        self.assertRedirects(response, reverse("website:confirmation", args=[reservation.reference]))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(reservation.reference, mail.outbox[0].body)

        self.client.post(reverse("website:cancel", args=[reservation.reference]))
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.Status.CANCELLED)

    def test_sold_out_room_shows_an_error(self):
        self.post_booking()
        response = self.post_booking()
        self.assertContains(response, "fully booked")
        self.assertEqual(Reservation.objects.count(), 1)

    def test_manage_booking_requires_reference_and_email(self):
        self.post_booking()
        reservation = Reservation.objects.get()
        stranger = Client()
        manage_url = reverse("website:manage", args=[reservation.reference])
        self.assertRedirects(stranger.get(manage_url), reverse("website:lookup"))

        wrong = stranger.post(reverse("website:lookup"), {"reference": reservation.reference, "email": "x@example.com"})
        self.assertContains(wrong, "find a booking matching")

        right = stranger.post(
            reverse("website:lookup"),
            {"reference": reservation.reference.lower(), "email": GUEST["guest_email"].upper()},
        )
        self.assertRedirects(right, manage_url)

    def test_search_shows_live_availability(self):
        response = self.client.get(reverse("website:search"), {"check_in": days(1), "check_out": days(2), "guests": 2})
        self.assertContains(response, self.room_type.name)
        self.assertContains(response, "Only 1 left")

    def test_search_without_dates_lists_rooms(self):
        response = self.client.get(reverse("website:search"))
        self.assertContains(response, "Pick your dates")
        self.assertContains(response, self.room_type.get_absolute_url())
