from datetime import timedelta

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.permissions import FRONT_DESK, role_required
from apps.dashboard.utils import paginate
from apps.website.forms import AvailabilityForm

from . import services
from .forms import CheckInForm, ReservationFilterForm, StaffReservationForm
from .models import Reservation

QUICK_VIEWS = {
    "arrivals": ("Arrivals today", lambda qs, today: qs.filter(status=Reservation.Status.CONFIRMED, check_in=today)),
    "departures": (
        "Departures today",
        lambda qs, today: qs.filter(status=Reservation.Status.CHECKED_IN, check_out__lte=today),
    ),
    "in_house": ("In-house", lambda qs, today: qs.filter(status=Reservation.Status.CHECKED_IN)),
    "upcoming": ("Upcoming", lambda qs, today: qs.filter(status=Reservation.Status.CONFIRMED, check_in__gte=today)),
}


def _get_reservation(reference):
    return get_object_or_404(Reservation.objects.select_related("room_type", "room"), reference=reference)


@role_required(FRONT_DESK)
def reservation_list(request):
    today = timezone.localdate()
    form = ReservationFilterForm(request.GET or None)
    reservations = Reservation.objects.select_related("room_type", "room")
    view = request.GET.get("view", "")
    if view in QUICK_VIEWS:
        reservations = QUICK_VIEWS[view][1](reservations, today)
    if form.is_valid():
        data = form.cleaned_data
        if data["q"]:
            reservations = reservations.filter(
                Q(reference__icontains=data["q"]) | Q(guest_name__icontains=data["q"])
                | Q(guest_email__icontains=data["q"])
            )
        if data["status"]:
            reservations = reservations.filter(status=data["status"])
        if data["date"]:
            reservations = reservations.filter(check_in__lte=data["date"], check_out__gt=data["date"])
    context = {
        "form": form,
        "page": paginate(request, reservations),
        "view": view,
        "quick_views": [(key, label) for key, (label, _) in QUICK_VIEWS.items()],
    }
    if request.htmx and request.htmx.target == "results":
        return render(request, "reservations/partials/table.html", context)
    return render(request, "reservations/list.html", context)


@role_required(FRONT_DESK)
def reservation_create(request):
    today = timezone.localdate()
    form = StaffReservationForm(
        request.POST or None,
        initial={"check_in": today, "check_out": today + timedelta(days=1), "adults": 1,
                 "source": Reservation.Source.WALK_IN},
    )
    if request.method == "POST" and form.is_valid():
        try:
            reservation = services.create_reservation(**form.cleaned_data, created_by=request.user)
        except services.BookingError as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, f"Reservation {reservation.reference} created.")
            return redirect(reservation)
    return render(request, "reservations/form.html", {"form": form})


@role_required(FRONT_DESK)
def availability(request):
    """HTMX partial: availability per room type for the dates on the staff booking form."""
    stay = AvailabilityForm(
        {"check_in": request.GET.get("check_in"), "check_out": request.GET.get("check_out"), "guests": 1}
    )
    results = None
    if stay.is_valid():
        results = services.search_availability(stay.cleaned_data["check_in"], stay.cleaned_data["check_out"])
    return render(request, "reservations/partials/availability.html", {"stay": stay, "results": results})


@role_required(FRONT_DESK)
def reservation_detail(request, reference):
    reservation = _get_reservation(reference)
    context = {
        "reservation": reservation,
        "orders": reservation.orders.prefetch_related("items__menu_item"),
        "invoice": getattr(reservation, "invoice", None),
    }
    return render(request, "reservations/detail.html", context)


@role_required(FRONT_DESK)
def check_in(request, reference):
    reservation = _get_reservation(reference)
    if not reservation.can_check_in:
        messages.error(request, "This reservation cannot be checked in.")
        return redirect(reservation)
    form = CheckInForm(request.POST or None, rooms=services.assignable_rooms(reservation))
    if request.method == "POST" and form.is_valid():
        try:
            services.check_in(reservation, form.cleaned_data["room"])
        except services.BookingError as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, f"{reservation.guest_name} checked in to {reservation.room}.")
            return redirect(reservation)
    return render(request, "reservations/check_in.html", {"reservation": reservation, "form": form})


@require_POST
@role_required(FRONT_DESK)
def check_out(request, reference):
    reservation = _get_reservation(reference)
    try:
        invoice = services.check_out(reservation)
    except services.BookingError as exc:
        messages.error(request, str(exc))
        return redirect(reservation)
    messages.success(request, f"{reservation.guest_name} checked out. Invoice {invoice.number} is ready.")
    return redirect(invoice)


@require_POST
@role_required(FRONT_DESK)
def cancel(request, reference):
    reservation = _get_reservation(reference)
    try:
        services.cancel(reservation, by_staff=True)
    except services.BookingError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f"Reservation {reservation.reference} cancelled.")
    return redirect(reservation)


@require_POST
@role_required(FRONT_DESK)
def no_show(request, reference):
    reservation = _get_reservation(reference)
    try:
        services.mark_no_show(reservation)
    except services.BookingError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f"Reservation {reservation.reference} marked as no-show.")
    return redirect(reservation)
