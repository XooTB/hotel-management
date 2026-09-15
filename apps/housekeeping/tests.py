from django.test import TestCase

from apps.rooms.models import Room
from apps.testing import make_room_type, make_rooms

from .models import HousekeepingTask
from .services import create_task, set_status

Status, TaskType = HousekeepingTask.Status, HousekeepingTask.TaskType


class HousekeepingTests(TestCase):
    def setUp(self):
        (self.room,) = make_rooms(make_room_type(), 1)

    def test_room_is_released_only_when_every_task_is_done(self):
        self.room.status = Room.Status.CLEANING
        self.room.save()
        cleaning = create_task(room=self.room)
        inspection = create_task(room=self.room, task_type=TaskType.INSPECTION)

        set_status(cleaning, Status.DONE)
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, Room.Status.CLEANING)

        set_status(inspection, Status.DONE)
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, Room.Status.AVAILABLE)

    def test_maintenance_task_takes_room_out_of_service(self):
        create_task(room=self.room, task_type=TaskType.MAINTENANCE)
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, Room.Status.MAINTENANCE)
