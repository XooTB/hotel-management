from django.urls import path

from . import views

app_name = "staff"

urlpatterns = [
    path("", views.StaffListView.as_view(), name="list"),
    path("new/", views.StaffCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", views.StaffUpdateView.as_view(), name="update"),
    path("shifts/", views.shift_schedule, name="shifts"),
    path("shifts/new/", views.ShiftCreateView.as_view(), name="shift_create"),
    path("shifts/<int:pk>/edit/", views.ShiftUpdateView.as_view(), name="shift_update"),
    path("shifts/<int:pk>/delete/", views.ShiftDeleteView.as_view(), name="shift_delete"),
]
