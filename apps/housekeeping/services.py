from django.db import transaction
from django.utils import timezone

from apps.rooms.models import Room

from .models import HousekeepingTask

OPEN_STATUSES = (HousekeepingTask.Status.PENDING, HousekeepingTask.Status.IN_PROGRESS)


def create_task(**fields):
    task = HousekeepingTask.objects.create(**fields)
    room = task.room
    if task.task_type == HousekeepingTask.TaskType.MAINTENANCE and room.status == Room.Status.AVAILABLE:
        room.status = Room.Status.MAINTENANCE
        room.save(update_fields=["status"])
    return task


def set_status(task, status):
    with transaction.atomic():
        task.status = status
        task.completed_at = timezone.now() if status == HousekeepingTask.Status.DONE else None
        task.save(update_fields=["status", "completed_at"])
        room = task.room
        no_open_tasks = not room.housekeeping_tasks.filter(status__in=OPEN_STATUSES).exists()
        if status == HousekeepingTask.Status.DONE and no_open_tasks and room.status in (
            Room.Status.CLEANING,
            Room.Status.MAINTENANCE,
        ):
            room.status = Room.Status.AVAILABLE
            room.save(update_fields=["status"])
    return task
