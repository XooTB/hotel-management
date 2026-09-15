"""Small factories shared by the test suites."""

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from apps.rooms.models import Room, RoomType

GUEST = {"guest_name": "Ada Lovelace", "guest_email": "ada@example.com", "guest_phone": "+1 555 0100"}


def days(offset):
    return timezone.localdate() + timedelta(days=offset)


def make_room_type(**fields):
    values = {"name": "Deluxe", "slug": "deluxe", "short_description": "A lovely room",
              "nightly_rate": Decimal("100.00"), "capacity": 2}
    values.update(fields)
    return RoomType.objects.create(**values)


def make_rooms(room_type, count, first_number=101):
    return [Room.objects.create(number=str(first_number + i), room_type=room_type) for i in range(count)]
