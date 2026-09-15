from django.urls import path

from . import views

app_name = "housekeeping"

urlpatterns = [
    path("", views.task_list, name="list"),
    path("new/", views.task_create, name="create"),
    path("<int:pk>/edit/", views.TaskUpdateView.as_view(), name="update"),
    path("<int:pk>/status/", views.task_set_status, name="set_status"),
]
