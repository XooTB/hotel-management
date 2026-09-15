from django.conf import settings
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("", include("apps.website.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("dashboard/reservations/", include("apps.reservations.urls")),
    path("dashboard/rooms/", include("apps.rooms.urls")),
    path("dashboard/housekeeping/", include("apps.housekeeping.urls")),
    path("dashboard/restaurant/", include("apps.restaurant.urls")),
    path("dashboard/billing/", include("apps.billing.urls")),
    path("dashboard/staff/", include("apps.staff.urls")),
    # The only file route: uploaded room photos, served by Django itself.
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
