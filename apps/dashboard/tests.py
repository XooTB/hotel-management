import shutil
import tempfile
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.accounts.models import User
from apps.restaurant.models import MenuItem
from apps.rooms.models import RoomType

# The demo seed uploads photos; keep them out of the project's media folder.
TEST_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class DashboardAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def test_each_role_only_reaches_its_own_areas(self):
        expected = {
            "manager": {"/dashboard/reports/": 200, "/dashboard/staff/": 200, "/dashboard/reservations/": 200},
            "reception": {"/dashboard/reservations/": 200, "/dashboard/housekeeping/": 200,
                          "/dashboard/reports/": 403, "/dashboard/staff/": 403},
            "housekeeping": {"/dashboard/rooms/": 200, "/dashboard/housekeeping/": 200,
                             "/dashboard/reservations/": 403, "/dashboard/billing/": 403},
            "restaurant": {"/dashboard/restaurant/": 200, "/dashboard/rooms/": 403, "/dashboard/billing/": 403},
        }
        for username, urls in expected.items():
            self.client.force_login(User.objects.get(username=username))
            for url, status in urls.items():
                with self.subTest(user=username, url=url):
                    self.assertEqual(self.client.get(url).status_code, status)

    def test_anonymous_users_are_sent_to_login(self):
        response = self.client.get("/dashboard/reservations/")
        self.assertRedirects(response, "/accounts/login/?next=/dashboard/reservations/")

    def test_main_pages_render_with_demo_data(self):
        self.client.force_login(User.objects.get(username="manager"))
        for url in ["/", "/rooms/", "/dashboard/", "/dashboard/reports/?days=90", "/dashboard/rooms/",
                    "/dashboard/restaurant/", "/dashboard/billing/", "/dashboard/staff/shifts/"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_demo_rooms_and_dishes_get_photos(self):
        self.assertFalse(RoomType.objects.filter(image="").exists())
        self.assertFalse(MenuItem.objects.filter(image="").exists())
        room_type = RoomType.objects.first()
        self.assertTrue(room_type.image.storage.exists(room_type.image.name))
        self.assertEqual(self.client.get("/static/img/site/hero.jpg").status_code, 200)

    def test_seed_fills_in_missing_photos_on_existing_data(self):
        RoomType.objects.update(image="")
        call_command("seed_demo", stdout=StringIO())
        self.assertFalse(RoomType.objects.filter(image="").exists())
