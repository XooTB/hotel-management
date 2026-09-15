"""Booking rules: availability, creating reservations, check-in/out, cancellation."""

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.billing.services import build_invoice
from apps.housekeeping.models import HousekeepingTask
from apps.rooms.models import Room, RoomType

from .models import Reservation

MAX_NIGHTS = 30


class BookingError(Exception):
    """A booking rule was violated; the message is safe to show to users."""


def overlapping(queryset, check_in, check_out):
    """Active reservations whose stay intersects [check_in, check_out)."""
    return queryset.filter(
        status__in=Reservation.ACTIVE_STATUSES,
        check_in__lt=check_out,
        check_out__gt=check_in,
    )


def validate_stay(check_in, check_out, *, allow_past=False):
    today = timezone.localdate()
    if check_out <= check_in:
        raise BookingError("Check-out must be after check-in.")
    if not allow_past and check_in < today:
        raise BookingError("Check-in date cannot be in the past.")
    if (check_out - check_in).days > MAX_NIGHTS:
        raise BookingError(f"Stays are limited to {MAX_NIGHTS} nights.")
    if check_in > today + timedelta(days=settings.HOTEL_MAX_ADVANCE_DAYS):
        raise BookingError("Bookings open one year in advance.")


def available_count(room_type, check_in, check_out, exclude=None):
    """Rooms of this type free on *every* night of the stay.

    Reservations hold inventory at room-type level (a specific room is assigned
    at check-in), so availability is the total bookable rooms minus the busiest
    night's bookings.
    """
    total = room_type.rooms.exclude(status=Room.Status.MAINTENANCE).count()
    if total == 0:
        return 0
    bookings = overlapping(Reservation.objects.filter(room_type=room_type), check_in, check_out)
    if exclude is not None:
        bookings = bookings.exclude(pk=exclude.pk)
    stays = list(bookings.values_list("check_in", "check_out"))
    peak = 0
    night = check_in
    while night < check_out:
        peak = max(peak, sum(1 for start, end in stays if start <= night < end))
        night += timedelta(days=1)
    return max(total - peak, 0)


def search_availability(check_in, check_out, guests=1):
    """Active room types that fit the party, annotated with `.available`."""
    results = []
    for room_type in RoomType.objects.filter(is_active=True, capacity__gte=guests).prefetch_related("amenities"):
        room_type.available = available_count(room_type, check_in, check_out)
        results.append(room_type)
    return results


def create_reservation(
    *,
    room_type,
    check_in,
    check_out,
    guest_name,
    guest_email,
    guest_phone,
    adults=1,
    children=0,
    special_requests="",
    source=Reservation.Source.ONLINE,
    created_by=None,
):
    validate_stay(check_in, check_out)
    if adults < 1:
        raise BookingError("At least one adult is required.")
    if adults + children > room_type.capacity:
        raise BookingError(f"{room_type.name} sleeps up to {room_type.capacity} guests.")

    with transaction.atomic():
        # Lock the room type so two concurrent bookings cannot take the last room.
        room_type = RoomType.objects.select_for_update().get(pk=room_type.pk)
        if not room_type.is_active or available_count(room_type, check_in, check_out) < 1:
            raise BookingError(f"Sorry, {room_type.name} is fully booked for those dates.")
        return Reservation.objects.create(
            room_type=room_type,
            check_in=check_in,
            check_out=check_out,
            adults=adults,
            children=children,
            guest_name=guest_name,
            guest_email=guest_email,
            guest_phone=guest_phone,
            special_requests=special_requests,
            nightly_rate=room_type.nightly_rate,
            source=source,
            created_by=created_by,
        )


def assignable_rooms(reservation):
    """Clean, available rooms of the booked type not already given to an overlapping stay."""
    taken = (
        overlapping(Reservation.objects.exclude(pk=reservation.pk), reservation.check_in, reservation.check_out)
        .exclude(room=None)
        .values("room_id")
    )
    return Room.objects.filter(room_type=reservation.room_type, status=Room.Status.AVAILABLE).exclude(pk__in=taken)


def check_in(reservation, room):
    if not reservation.can_check_in:
        raise BookingError("This reservation cannot be checked in.")
    with transaction.atomic():
        room = Room.objects.select_for_update().get(pk=room.pk)
        if not assignable_rooms(reservation).filter(pk=room.pk).exists():
            raise BookingError(f"{room} is not available for this stay.")
        reservation.room = room
        reservation.status = Reservation.Status.CHECKED_IN
        reservation.checked_in_at = timezone.now()
        reservation.save(update_fields=["room", "status", "checked_in_at", "updated_at"])
        room.status = Room.Status.OCCUPIED
        room.save(update_fields=["status"])
    return reservation


def check_out(reservation):
    """Close the stay, raise the invoice and send the room to housekeeping."""
    if not reservation.can_check_out:
        raise BookingError("Only checked-in guests can be checked out.")
    with transaction.atomic():
        invoice = build_invoice(reservation)
        reservation.status = Reservation.Status.CHECKED_OUT
        reservation.checked_out_at = timezone.now()
        reservation.save(update_fields=["status", "checked_out_at", "updated_at"])
        if reservation.room:
            reservation.room.status = Room.Status.CLEANING
            reservation.room.save(update_fields=["status"])
            HousekeepingTask.objects.create(
                room=reservation.room,
                task_type=HousekeepingTask.TaskType.CLEANING,
                priority=HousekeepingTask.Priority.HIGH,
                notes=f"Departure clean after {reservation.reference}",
            )
    return invoice


def cancel(reservation, *, by_staff=False):
    allowed = reservation.status == Reservation.Status.CONFIRMED if by_staff else reservation.can_cancel
    if not allowed:
        raise BookingError("This reservation can no longer be cancelled.")
    reservation.status = Reservation.Status.CANCELLED
    reservation.cancelled_at = timezone.now()
    reservation.save(update_fields=["status", "cancelled_at", "updated_at"])
    return reservation


def mark_no_show(reservation):
    if reservation.status != Reservation.Status.CONFIRMED or reservation.check_in > timezone.localdate():
        raise BookingError("Only confirmed arrivals from today or earlier can be marked as no-show.")
    reservation.status = Reservation.Status.NO_SHOW
    reservation.save(update_fields=["status", "updated_at"])
    return reservation
