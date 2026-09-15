from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, ListView, UpdateView

from apps.accounts.models import User
from apps.accounts.permissions import RoleRequiredMixin
from apps.dashboard.utils import DashboardDeleteView, DashboardFormMixin

from .forms import ShiftForm, StaffCreateForm, StaffUpdateForm
from .models import Shift


class StaffListView(RoleRequiredMixin, ListView):
    template_name = "staff/list.html"
    context_object_name = "staff_members"

    def get_queryset(self):
        today = timezone.localdate()
        return User.objects.annotate(
            upcoming_shifts=Count("shifts", filter=Q(shifts__date__gte=today))
        ).order_by("-is_active", "role", "first_name")


class StaffCreateView(DashboardFormMixin, CreateView):
    model = User
    form_class = StaffCreateForm
    title = "Add staff member"
    back_url_name = "staff:list"
    success_url = reverse_lazy("staff:list")
    success_message = "%(username)s can now sign in."


class StaffUpdateView(DashboardFormMixin, UpdateView):
    model = User
    form_class = StaffUpdateForm
    back_url_name = "staff:list"
    success_url = reverse_lazy("staff:list")
    success_message = "Staff details updated."


def _week_start(value):
    try:
        day = date.fromisoformat(value)
    except (TypeError, ValueError):
        day = timezone.localdate()
    return day - timedelta(days=day.weekday())


@login_required
def shift_schedule(request):
    start = _week_start(request.GET.get("week"))
    days = [start + timedelta(days=i) for i in range(7)]
    shifts = Shift.objects.filter(date__range=(days[0], days[-1])).select_related("staff")
    staff = User.objects.filter(is_active=True)
    if not request.user.is_manager:
        shifts = shifts.filter(staff=request.user)
        staff = staff.filter(pk=request.user.pk)
    by_cell = {}
    for shift in shifts:
        by_cell.setdefault((shift.staff_id, shift.date), []).append(shift)
    rows = [(member, [(day, by_cell.get((member.pk, day), [])) for day in days]) for member in staff]
    context = {
        "days": days,
        "rows": rows,
        "today": timezone.localdate(),
        "prev_week": start - timedelta(days=7),
        "next_week": start + timedelta(days=7),
    }
    return render(request, "staff/shifts.html", context)


class ShiftCreateView(DashboardFormMixin, CreateView):
    model = Shift
    form_class = ShiftForm
    title = "Schedule shift"
    back_url_name = "staff:shifts"
    success_url = reverse_lazy("staff:shifts")
    success_message = "Shift scheduled."

    def get_initial(self):
        return {"staff": self.request.GET.get("staff"), "date": self.request.GET.get("date"),
                "start_time": "07:00", "end_time": "15:00"}


class ShiftUpdateView(DashboardFormMixin, UpdateView):
    model = Shift
    form_class = ShiftForm
    title = "Edit shift"
    back_url_name = "staff:shifts"
    delete_url_name = "staff:shift_delete"
    success_url = reverse_lazy("staff:shifts")
    success_message = "Shift updated."


class ShiftDeleteView(DashboardDeleteView):
    model = Shift
    success_url_name = "staff:shifts"
