from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.accounts.models import User


class DashboardAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())

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
