from django.urls import path

from . import views

app_name = "reservations"

urlpatterns = [
    path("", views.reservation_list, name="list"),
    path("new/", views.reservation_create, name="create"),
    path("availability/", views.availability, name="availability"),
    path("<str:reference>/", views.reservation_detail, name="detail"),
    path("<str:reference>/check-in/", views.check_in, name="check_in"),
    path("<str:reference>/check-out/", views.check_out, name="check_out"),
    path("<str:reference>/cancel/", views.cancel, name="cancel"),
    path("<str:reference>/no-show/", views.no_show, name="no_show"),
]
