from django.urls import path

from . import views

app_name = "rooms"

urlpatterns = [
    path("", views.room_list, name="list"),
    path("new/", views.RoomCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", views.RoomUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", views.RoomDeleteView.as_view(), name="delete"),
    path("<int:pk>/status/", views.room_set_status, name="set_status"),
    path("types/", views.RoomTypeListView.as_view(), name="type_list"),
    path("types/new/", views.RoomTypeCreateView.as_view(), name="type_create"),
    path("types/<int:pk>/edit/", views.RoomTypeUpdateView.as_view(), name="type_update"),
    path("types/<int:pk>/delete/", views.RoomTypeDeleteView.as_view(), name="type_delete"),
]
