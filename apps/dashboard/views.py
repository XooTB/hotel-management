from collections import Counter, defaultdict
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import render
from django.utils import timezone

from apps.accounts import permissions as perms
from apps.billing.models import Invoice
from apps.housekeeping.models import HousekeepingTask
from apps.housekeeping.services import OPEN_STATUSES
from apps.reservations.models import Reservation
from apps.restaurant.models import Order, OrderItem
from apps.rooms.models import Room

Status = Reservation.Status


@login_required
def home(request):
    user = request.user
    today = timezone.localdate()
    context = {"today": today, "my_shifts": user.shifts.filter(date__gte=today)[:5]}

    if perms.user_allowed(user, perms.FRONT_DESK):
        total_rooms = Room.objects.count()
        occupied = Room.objects.filter(status=Room.Status.OCCUPIED).count()
        arrivals = Reservation.objects.filter(status=Status.CONFIRMED, check_in=today).select_related("room_type")
        departures = Reservation.objects.filter(status=Status.CHECKED_IN, check_out__lte=today).select_related(
            "room", "room_type"
        )
        context.update(
            show_front_desk=True,
            arrivals=arrivals,
            departures=departures,
            stats=[
                {"label": "Occupancy", "value": f"{round(100 * occupied / total_rooms) if total_rooms else 0}%",
                 "sub": f"{occupied} of {total_rooms} rooms", "icon": "bed"},
                {"label": "Arrivals today", "value": arrivals.count(), "sub": "awaiting check-in", "icon": "log-in"},
                {"label": "Departures today", "value": departures.count(), "sub": "due to check out", "icon": "logout"},
                {"label": "Unpaid invoices", "value": Invoice.objects.filter(status=Invoice.Status.UNPAID).count(),
                 "sub": "settle at front desk", "icon": "receipt"},
            ],
        )

    if perms.user_allowed(user, perms.HOUSEKEEPING):
        counts = dict(Room.objects.values_list("status").annotate(n=Count("id")))
        tasks = HousekeepingTask.objects.filter(status__in=OPEN_STATUSES).select_related("room", "assigned_to")
        if user.role == user.Role.HOUSEKEEPING and not user.is_manager:
            tasks = tasks.filter(Q(assigned_to=user) | Q(assigned_to=None))
        context.update(
            show_housekeeping=True,
            room_statuses=[(value, label, counts.get(value, 0)) for value, label in Room.Status.choices],
            open_tasks=tasks.order_by("-priority", "created_at")[:8],
        )

    if perms.user_allowed(user, perms.RESTAURANT):
        context.update(
            show_restaurant=True,
            active_orders=Order.objects.filter(status__in=[Order.Status.PLACED, Order.Status.PREPARING])
            .select_related("reservation__room")
            .prefetch_related("items__menu_item")[:6],
        )

    return render(request, "dashboard/home.html", context)


def _as_float(value):
    return float(value or Decimal("0"))


@perms.role_required(perms.MANAGEMENT)
def reports(request):
    today = timezone.localdate()
    days = int(request.GET.get("days", 30)) if request.GET.get("days") in {"7", "30", "90"} else 30
    start = today - timedelta(days=days - 1)
    dates = [start + timedelta(days=i) for i in range(days)]
    total_rooms = Room.objects.count() or 1

    # Occupancy: nights actually stayed (checked in or out) per calendar day.
    stays = list(
        Reservation.objects.filter(
            status__in=[Status.CHECKED_IN, Status.CHECKED_OUT], check_in__lte=today, check_out__gt=start
        ).values_list("check_in", "check_out", "nightly_rate")
    )
    occupied_per_day = [sum(1 for a, b, _ in stays if a <= d < b) for d in dates]
    occupancy = [round(100 * n / total_rooms, 1) for n in occupied_per_day]
    room_nights = sum(occupied_per_day)
    room_revenue = sum((rate for a, b, rate in stays for d in dates if a <= d < b), Decimal("0"))

    # Revenue: paid invoices by payment date.
    revenue_by_day = defaultdict(Decimal)
    paid = Invoice.objects.filter(status=Invoice.Status.PAID, paid_at__date__gte=start).prefetch_related("lines")
    for invoice in paid:
        revenue_by_day[timezone.localdate(invoice.paid_at)] += invoice.total
    revenue = [_as_float(revenue_by_day[d]) for d in dates]

    bookings = Reservation.objects.filter(created_at__date__gte=start)
    by_type = list(bookings.values("room_type__name").annotate(n=Count("id")).order_by("-n"))
    by_source = Counter(dict(bookings.values_list("source").annotate(n=Count("id"))))
    cancelled = bookings.filter(status=Status.CANCELLED).count()

    orders = Order.objects.filter(created_at__date__gte=start, status=Order.Status.SERVED)
    restaurant_sales = sum((o.total for o in orders.prefetch_related("items")), Decimal("0"))
    top_items = (
        OrderItem.objects.filter(order__in=orders)
        .values("menu_item__name")
        .annotate(qty=Sum("quantity"))
        .order_by("-qty")[:5]
    )

    chart_data = {
        "labels": [d.strftime("%d %b") for d in dates],
        "occupancy": occupancy,
        "revenue": revenue,
        "byType": {"labels": [row["room_type__name"] for row in by_type], "values": [row["n"] for row in by_type]},
        "bySource": {
            "labels": [label for value, label in Reservation.Source.choices],
            "values": [by_source.get(value, 0) for value, _ in Reservation.Source.choices],
        },
    }
    total_bookings = bookings.count()
    context = {
        "days": days,
        "kpis": [
            {"label": "Revenue collected", "value": sum(revenue_by_day.values(), Decimal("0")), "money": True},
            {"label": "Average occupancy", "value": f"{round(sum(occupancy) / days, 1)}%"},
            {"label": "Avg. daily rate", "value": room_revenue / room_nights if room_nights else 0, "money": True},
            {"label": "Restaurant sales", "value": restaurant_sales, "money": True},
            {"label": "New bookings", "value": total_bookings},
            {"label": "Cancellation rate",
             "value": f"{round(100 * cancelled / total_bookings) if total_bookings else 0}%"},
        ],
        "top_items": top_items,
        "daily_rows": list(zip(dates, occupancy, revenue))[::-1],
        "chart_data": chart_data,
    }
    return render(request, "dashboard/reports.html", context)


