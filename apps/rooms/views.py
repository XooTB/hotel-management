from itertools import groupby

from django.contrib import messages
from django.db.models import Count
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, ListView, UpdateView

from apps.accounts.permissions import HOUSEKEEPING, MANAGEMENT, role_required
from apps.accounts.permissions import RoleRequiredMixin
from apps.dashboard.utils import DashboardDeleteView, DashboardFormMixin
from apps.reservations.models import Reservation

from .forms import RoomForm, RoomTypeForm
from .models import Room, RoomType

# Occupied is only set/cleared through check-in and check-out.
MANUAL_STATUSES = [choice for choice in Room.Status.choices if choice[0] != Room.Status.OCCUPIED]


def _with_current_stays(rooms):
    stays = {
        r.room_id: r
        for r in Reservation.objects.filter(status=Reservation.Status.CHECKED_IN, room__isnull=False)
    }
    for room in rooms:
        room.current_stay = stays.get(room.pk)
    return rooms


@role_required(HOUSEKEEPING)
def room_list(request):
    status = request.GET.get("status", "")
    rooms = Room.objects.select_related("room_type")
    if status in Room.Status.values:
        rooms = rooms.filter(status=status)
    rooms = _with_current_stays(list(rooms))
    counts = dict(Room.objects.values_list("status").annotate(n=Count("id")))
    context = {
        "floors": [(floor, list(items)) for floor, items in groupby(rooms, key=lambda r: r.floor)],
        "status": status,
        "status_tabs": [(value, label, counts.get(value, 0)) for value, label in Room.Status.choices],
        "total": sum(counts.values()),
        "manual_statuses": MANUAL_STATUSES,
    }
    return render(request, "rooms/list.html", context)


@require_POST
@role_required(HOUSEKEEPING)
def room_set_status(request, pk):
    room = get_object_or_404(Room.objects.select_related("room_type"), pk=pk)
    new_status = request.POST.get("status")
    if room.status == Room.Status.OCCUPIED or new_status not in dict(MANUAL_STATUSES):
        return HttpResponseBadRequest("Status cannot be changed manually.")
    room.status = new_status
    room.save(update_fields=["status"])
    if request.htmx:
        room.current_stay = None
        return render(request, "rooms/partials/room_card.html", {"room": room, "manual_statuses": MANUAL_STATUSES})
    messages.success(request, f"{room} marked as {room.get_status_display().lower()}.")
    return redirect("rooms:list")


class RoomCreateView(DashboardFormMixin, CreateView):
    model = Room
    form_class = RoomForm
    title = "Add room"
    back_url_name = "rooms:list"
    success_url = reverse_lazy("rooms:list")
    success_message = "Room %(number)s added."


class RoomUpdateView(DashboardFormMixin, UpdateView):
    model = Room
    form_class = RoomForm
    back_url_name = "rooms:list"
    delete_url_name = "rooms:delete"
    success_url = reverse_lazy("rooms:list")
    success_message = "Room %(number)s updated."


class RoomDeleteView(DashboardDeleteView):
    model = Room
    success_url_name = "rooms:list"


class RoomTypeListView(RoleRequiredMixin, ListView):
    allowed_roles = MANAGEMENT
    template_name = "rooms/type_list.html"
    context_object_name = "room_types"

    def get_queryset(self):
        return RoomType.objects.annotate(room_count=Count("rooms")).order_by("nightly_rate")


class RoomTypeCreateView(DashboardFormMixin, CreateView):
    model = RoomType
    form_class = RoomTypeForm
    title = "Add room type"
    back_url_name = "rooms:type_list"
    success_url = reverse_lazy("rooms:type_list")
    success_message = "%(name)s added."


class RoomTypeUpdateView(DashboardFormMixin, UpdateView):
    model = RoomType
    form_class = RoomTypeForm
    back_url_name = "rooms:type_list"
    delete_url_name = "rooms:type_delete"
    success_url = reverse_lazy("rooms:type_list")
    success_message = "%(name)s updated."


class RoomTypeDeleteView(DashboardDeleteView):
    model = RoomType
    success_url_name = "rooms:type_list"
