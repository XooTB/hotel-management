from django.conf import settings
from django.urls import include, path, re_path
from django.views.decorators.cache import cache_control
from django.views.static import serve

# Photos rarely change, so let browsers keep them for a day.
cached_serve = cache_control(public=True, max_age=60 * 60 * 24)(serve)

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
    # Files served by Django itself: site photos from the repo, and uploaded photos.
    re_path(r"^static/(?P<path>.*)$", cached_serve, {"document_root": settings.STATIC_ROOT}),
    re_path(r"^media/(?P<path>.*)$", cached_serve, {"document_root": settings.MEDIA_ROOT}),
]
