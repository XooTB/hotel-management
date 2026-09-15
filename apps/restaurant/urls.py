from django.urls import path

from . import views

app_name = "restaurant"

urlpatterns = [
    path("", views.order_board, name="order_list"),
    path("orders/new/", views.order_create, name="order_create"),
    path("orders/<int:pk>/status/", views.order_set_status, name="order_set_status"),
    path("orders/<int:pk>/paid/", views.order_mark_paid, name="order_mark_paid"),
    path("menu/", views.menu, name="menu"),
    path("menu/items/new/", views.MenuItemCreateView.as_view(), name="item_create"),
    path("menu/items/<int:pk>/edit/", views.MenuItemUpdateView.as_view(), name="item_update"),
    path("menu/items/<int:pk>/toggle/", views.menu_item_toggle, name="item_toggle"),
    path("menu/categories/new/", views.MenuCategoryCreateView.as_view(), name="category_create"),
]
