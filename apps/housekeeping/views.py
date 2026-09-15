from django.contrib import messages
from django.db.models import Case, IntegerField, Value, When
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import UpdateView

from apps.accounts.permissions import HOUSEKEEPING, role_required
from apps.dashboard.utils import DashboardFormMixin, paginate

from . import services
from .forms import TaskForm
from .models import HousekeepingTask

PRIORITY_ORDER = Case(
    When(priority=HousekeepingTask.Priority.HIGH, then=Value(0)),
    When(priority=HousekeepingTask.Priority.NORMAL, then=Value(1)),
    default=Value(2),
    output_field=IntegerField(),
)


@role_required(HOUSEKEEPING)
def task_list(request):
    status = request.GET.get("status", "open")
    tasks = HousekeepingTask.objects.select_related("room__room_type", "assigned_to")
    if status == "open":
        tasks = tasks.filter(status__in=services.OPEN_STATUSES)
    elif status in HousekeepingTask.Status.values:
        tasks = tasks.filter(status=status)
    mine = request.GET.get("mine") == "1"
    if mine:
        tasks = tasks.filter(assigned_to=request.user)
    tasks = tasks.order_by(PRIORITY_ORDER, "created_at") if status == "open" else tasks.order_by("-created_at")
    context = {
        "page": paginate(request, tasks, per_page=25),
        "status": status,
        "mine": mine,
        "tabs": [("open", "Open"), *HousekeepingTask.Status.choices, ("all", "All")],
        "statuses": HousekeepingTask.Status.choices,
    }
    return render(request, "housekeeping/list.html", context)


@role_required(HOUSEKEEPING)
def task_create(request):
    form = TaskForm(request.POST or None, initial={"room": request.GET.get("room")})
    if request.method == "POST" and form.is_valid():
        task = services.create_task(**form.cleaned_data)
        messages.success(request, f"Task created for {task.room}.")
        return redirect("housekeeping:list")
    return render(
        request, "dashboard/form.html",
        {"form": form, "title": "New housekeeping task", "back_url": reverse_lazy("housekeeping:list")},
    )


class TaskUpdateView(DashboardFormMixin, UpdateView):
    allowed_roles = HOUSEKEEPING
    model = HousekeepingTask
    form_class = TaskForm
    title = "Edit task"
    back_url_name = "housekeeping:list"
    success_url = reverse_lazy("housekeeping:list")
    success_message = "Task updated."


@require_POST
@role_required(HOUSEKEEPING)
def task_set_status(request, pk):
    task = get_object_or_404(HousekeepingTask.objects.select_related("room", "assigned_to"), pk=pk)
    status = request.POST.get("status")
    if status not in HousekeepingTask.Status.values:
        return HttpResponseBadRequest("Unknown status.")
    services.set_status(task, status)
    if request.htmx:
        return render(request, "housekeeping/partials/task_row.html", {"task": task})
    return redirect("housekeeping:list")
