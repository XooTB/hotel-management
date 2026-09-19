from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.htmx import is_htmx
from apps.reservations import services
from apps.reservations.models import Reservation
from apps.restaurant.models import MenuItem
from apps.rooms.models import RoomType

from .forms import AvailabilityForm, BookingForm, LookupForm

SESSION_KEY = "guest_bookings"


def _remember_booking(request, reservation):
    """Mark a booking as verified for this browser session (guests have no accounts)."""
    references = set(request.session.get(SESSION_KEY, []))
    references.add(reservation.reference)
    request.session[SESSION_KEY] = sorted(references)


def _verified_booking(request, reference):
    if reference not in request.session.get(SESSION_KEY, []):
        return None
    return Reservation.objects.select_related("room_type", "room").filter(reference=reference).first()


def _send_confirmation(request, reservation):
    manage_url = request.build_absolute_uri(reverse("website:lookup"))
    body = render_to_string(
        "website/email/confirmation.txt",
        {"reservation": reservation, "manage_url": manage_url, "HOTEL_NAME": settings.HOTEL_NAME,
         "CURRENCY": settings.HOTEL_CURRENCY},
    )
    send_mail(
        f"Your booking at {settings.HOTEL_NAME} – {reservation.reference}",
        body,
        settings.DEFAULT_FROM_EMAIL,
        [reservation.guest_email],
        fail_silently=True,
    )


def home(request):
    context = {
        "form": AvailabilityForm.with_defaults(),
        "room_types": RoomType.objects.filter(is_active=True).prefetch_related("amenities")[:3],
        "dishes": MenuItem.objects.filter(is_available=True).exclude(image="").order_by("-price")[:4],
    }
    return render(request, "website/home.html", context)


def room_list(request):
    room_types = RoomType.objects.filter(is_active=True).prefetch_related("amenities")
    return render(request, "website/room_list.html", {"room_types": room_types})


def room_detail(request, slug):
    room_type = get_object_or_404(RoomType.objects.prefetch_related("amenities"), slug=slug, is_active=True)
    form = AvailabilityForm.with_defaults(request.GET if "check_in" in request.GET else None)
    available = None
    if form.is_bound and form.is_valid():
        data = form.cleaned_data
        available = services.available_count(room_type, data["check_in"], data["check_out"])
    context = {"room_type": room_type, "form": form, "available": available}
    template = "website/partials/room_availability.html" if is_htmx(request) else "website/room_detail.html"
    return render(request, template, context)


def search(request):
    form = AvailabilityForm.with_defaults(request.GET if "check_in" in request.GET else None)
    results = nights = None
    if form.is_bound and form.is_valid():
        data = form.cleaned_data
        nights = (data["check_out"] - data["check_in"]).days
        results = services.search_availability(data["check_in"], data["check_out"], data["guests"])
    template = "website/partials/search_results.html" if is_htmx(request) else "website/search.html"
    return render(request, template, {"form": form, "results": results, "nights": nights})


def book(request, slug):
    room_type = get_object_or_404(RoomType, slug=slug, is_active=True)
    source = request.POST if request.method == "POST" else request.GET
    stay = AvailabilityForm(
        {"check_in": source.get("check_in"), "check_out": source.get("check_out"), "guests": 1}
    )
    if not stay.is_valid():
        messages.error(request, "Please choose valid stay dates first.")
        return redirect("website:room_detail", slug=slug)
    check_in, check_out = stay.cleaned_data["check_in"], stay.cleaned_data["check_out"]

    if request.method == "POST":
        form = BookingForm(request.POST, room_type=room_type)
        if form.is_valid():
            try:
                reservation = services.create_reservation(room_type=room_type, **form.cleaned_data)
            except services.BookingError as exc:
                form.add_error(None, str(exc))
            else:
                _remember_booking(request, reservation)
                _send_confirmation(request, reservation)
                return redirect("website:confirmation", reference=reservation.reference)
    else:
        guests = request.GET.get("guests", "2")
        adults = min(int(guests), room_type.capacity) if guests.isdigit() and int(guests) > 0 else 2
        form = BookingForm(
            room_type=room_type,
            initial={"check_in": check_in, "check_out": check_out, "adults": adults, "children": 0},
        )

    nights = (check_out - check_in).days
    context = {
        "room_type": room_type,
        "form": form,
        "check_in": check_in,
        "check_out": check_out,
        "nights": nights,
        "total": room_type.nightly_rate * nights,
        "available": services.available_count(room_type, check_in, check_out),
    }
    return render(request, "website/book.html", context)


def confirmation(request, reference):
    reservation = _verified_booking(request, reference)
    if reservation is None:
        return redirect("website:lookup")
    return render(request, "website/confirmation.html", {"reservation": reservation})


def lookup(request):
    form = LookupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        reservation = Reservation.objects.filter(
            reference=form.cleaned_data["reference"],
            guest_email__iexact=form.cleaned_data["email"],
        ).first()
        if reservation:
            _remember_booking(request, reservation)
            return redirect("website:manage", reference=reservation.reference)
        form.add_error(None, "We couldn't find a booking matching those details.")
    return render(request, "website/lookup.html", {"form": form})


def manage(request, reference):
    reservation = _verified_booking(request, reference)
    if reservation is None:
        messages.info(request, "Please confirm your booking reference and email.")
        return redirect("website:lookup")
    return render(request, "website/manage.html", {"reservation": reservation})


@require_POST
def cancel(request, reference):
    reservation = _verified_booking(request, reference)
    if reservation is None:
        return redirect("website:lookup")
    try:
        services.cancel(reservation)
    except services.BookingError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Your booking has been cancelled.")
    return redirect("website:manage", reference=reference)
