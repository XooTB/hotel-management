from django.urls import path

from . import views

app_name = "website"

urlpatterns = [
    path("", views.home, name="home"),
    path("rooms/", views.room_list, name="room_list"),
    path("rooms/<slug:slug>/", views.room_detail, name="room_detail"),
    path("rooms/<slug:slug>/book/", views.book, name="book"),
    path("search/", views.search, name="search"),
    path("booking/manage/", views.lookup, name="lookup"),
    path("booking/<str:reference>/", views.manage, name="manage"),
    path("booking/<str:reference>/confirmed/", views.confirmation, name="confirmation"),
    path("booking/<str:reference>/cancel/", views.cancel, name="cancel"),
]
