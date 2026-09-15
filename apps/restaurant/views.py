from django.contrib import messages
from django.db import transaction
from django.db.models import Prefetch
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, UpdateView

from apps.accounts.permissions import RESTAURANT, role_required
from apps.dashboard.utils import DashboardFormMixin
from apps.htmx import is_htmx

from .forms import MenuCategoryForm, MenuItemForm, OrderForm
from .models import MenuCategory, MenuItem, Order, OrderItem


def _board_context():
    today = timezone.localdate()
    orders = Order.objects.select_related("reservation__room").prefetch_related("items__menu_item")
    return {
        "columns": [
            ("placed", "New", orders.filter(status=Order.Status.PLACED).order_by("created_at")),
            ("preparing", "Preparing", orders.filter(status=Order.Status.PREPARING).order_by("created_at")),
            ("served", "Served today", orders.filter(status=Order.Status.SERVED, created_at__date=today)),
        ]
    }


@role_required(RESTAURANT)
def order_board(request):
    template = "restaurant/partials/board.html" if is_htmx(request) else "restaurant/order_board.html"
    return render(request, template, _board_context())


@role_required(RESTAURANT)
def order_create(request):
    form = OrderForm(request.POST or None, initial={
            "order_type": request.GET.get("type", Order.OrderType.DINE_IN),
            "reservation": request.GET.get("reservation"),
            "charge_to_room": bool(request.GET.get("reservation")),
        },
    )
    categories = MenuCategory.objects.prefetch_related(
        Prefetch("items", queryset=MenuItem.objects.filter(is_available=True))
    )
    quantities = {}
    if request.method == "POST":
        for key, value in request.POST.items():
            if key.startswith("qty_") and key[4:].isdigit() and value.isdigit() and int(value) > 0:
                quantities[int(key[4:])] = min(int(value), 99)
        items = list(MenuItem.objects.filter(pk__in=quantities, is_available=True))
        if not items:
            form.add_error(None, "Add at least one menu item to the order.")
        if form.is_valid():
            with transaction.atomic():
                order = form.save(commit=False)
                order.created_by = request.user
                order.save()
                OrderItem.objects.bulk_create(
                    OrderItem(order=order, menu_item=item, quantity=quantities[item.pk], unit_price=item.price)
                    for item in items
                )
            messages.success(request, f"Order #{order.pk} sent to the kitchen.")
            return redirect("restaurant:order_list")
    return render(
        request, "restaurant/order_form.html",
        {"form": form, "categories": categories, "quantities": quantities},
    )


@require_POST
@role_required(RESTAURANT)
def order_set_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    status = request.POST.get("status")
    if status not in Order.Status.values:
        return HttpResponseBadRequest("Unknown status.")
    order.status = status
    order.save(update_fields=["status"])
    if is_htmx(request):
        return render(request, "restaurant/partials/board.html", _board_context())
    return redirect("restaurant:order_list")


@require_POST
@role_required(RESTAURANT)
def order_mark_paid(request, pk):
    order = get_object_or_404(Order, pk=pk, charge_to_room=False)
    order.is_paid = True
    order.save(update_fields=["is_paid"])
    if is_htmx(request):
        return render(request, "restaurant/partials/board.html", _board_context())
    return redirect("restaurant:order_list")


@role_required(RESTAURANT)
def menu(request):
    categories = MenuCategory.objects.prefetch_related("items")
    return render(request, "restaurant/menu.html", {"categories": categories})


@require_POST
@role_required(RESTAURANT)
def menu_item_toggle(request, pk):
    item = get_object_or_404(MenuItem, pk=pk)
    item.is_available = not item.is_available
    item.save(update_fields=["is_available"])
    if is_htmx(request):
        return render(request, "restaurant/partials/menu_item_row.html", {"item": item})
    return redirect("restaurant:menu")


class MenuItemCreateView(DashboardFormMixin, CreateView):
    allowed_roles = RESTAURANT
    model = MenuItem
    form_class = MenuItemForm
    title = "Add menu item"
    back_url_name = "restaurant:menu"
    success_url = reverse_lazy("restaurant:menu")
    success_message = "%(name)s added to the menu."


class MenuItemUpdateView(DashboardFormMixin, UpdateView):
    allowed_roles = RESTAURANT
    model = MenuItem
    form_class = MenuItemForm
    back_url_name = "restaurant:menu"
    success_url = reverse_lazy("restaurant:menu")
    success_message = "%(name)s updated."


class MenuCategoryCreateView(DashboardFormMixin, CreateView):
    allowed_roles = RESTAURANT
    model = MenuCategory
    form_class = MenuCategoryForm
    title = "Add menu category"
    back_url_name = "restaurant:menu"
    success_url = reverse_lazy("restaurant:menu")
    success_message = "Category %(name)s added."
