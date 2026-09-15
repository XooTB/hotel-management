"""Populate the database with a realistic demo hotel."""

import random
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.billing.models import Invoice
from apps.billing.services import build_invoice, mark_paid
from apps.housekeeping.models import HousekeepingTask
from apps.reservations.models import Reservation
from apps.restaurant.models import MenuCategory, MenuItem, Order, OrderItem
from apps.rooms.models import Amenity, Room, RoomType
from apps.staff.models import Shift

PASSWORD = "demo12345"
Role = User.Role

STAFF = [
    ("admin", "Alex", "Morgan", Role.MANAGER, True),
    ("manager", "Priya", "Shah", Role.MANAGER, False),
    ("reception", "Daniel", "Reyes", Role.RECEPTIONIST, False),
    ("reception2", "Mia", "Chen", Role.RECEPTIONIST, False),
    ("housekeeping", "Grace", "Okafor", Role.HOUSEKEEPING, False),
    ("housekeeping2", "Luis", "Ortega", Role.HOUSEKEEPING, False),
    ("restaurant", "Marco", "Rossi", Role.RESTAURANT, False),
]

ROOM_TYPES = [
    {
        "name": "Classic Queen", "slug": "classic-queen", "nightly_rate": "129.00", "capacity": 2,
        "bed_type": "Queen bed", "size_sqm": 24, "floor": 1, "count": 8,
        "short_description": "A calm, well-designed room for city breaks and business trips.",
        "description": "Soft linens, blackout curtains and a generous work desk make the Classic Queen an easy "
                       "place to land after a day out.\n\nOverlooks the old town courtyard.",
        "amenities": ["Free Wi-Fi", "Air conditioning", "Smart TV", "Work desk", "Rain shower"],
    },
    {
        "name": "Deluxe King", "slug": "deluxe-king", "nightly_rate": "189.00", "capacity": 2,
        "bed_type": "King bed", "size_sqm": 32, "floor": 2, "count": 6,
        "short_description": "More space, a king bed and floor-to-ceiling harbour views.",
        "description": "Our most popular room: a wide king bed facing the water, a lounge chair by the window "
                       "and a marble bathroom with a deep rain shower.",
        "amenities": ["Free Wi-Fi", "Air conditioning", "Smart TV", "Sea view", "Mini bar", "Nespresso machine",
                      "Rain shower"],
    },
    {
        "name": "Family Suite", "slug": "family-suite", "nightly_rate": "259.00", "capacity": 4,
        "bed_type": "King + sofa bed", "size_sqm": 48, "floor": 3, "count": 4,
        "short_description": "A separate living room and space for the whole family.",
        "description": "A king bedroom plus a living room with a sofa bed, dining table and kitchenette, so "
                       "everyone has room to spread out.",
        "amenities": ["Free Wi-Fi", "Air conditioning", "Smart TV", "Kitchenette", "Sofa bed", "Bathtub",
                      "Balcony"],
    },
    {
        "name": "Harbour Penthouse", "slug": "harbour-penthouse", "nightly_rate": "480.00", "capacity": 4,
        "bed_type": "Super king bed", "size_sqm": 90, "floor": 4, "count": 2,
        "short_description": "The top floor, a wraparound terrace and the best sunset in town.",
        "description": "Two bedrooms, a private terrace running the length of the building and lounge access "
                       "included. Ideal for special occasions.",
        "amenities": ["Free Wi-Fi", "Air conditioning", "Smart TV", "Sea view", "Balcony", "Bathtub",
                      "Mini bar", "Nespresso machine", "Lounge access"],
    },
]

MENU = {
    "Breakfast": [("Full harbour breakfast", "Eggs, bacon, sausage, beans, toast", "18.00"),
                  ("Avocado sourdough", "Poached eggs, chilli, lime", "14.50"),
                  ("Berry pancakes", "Maple syrup, crème fraîche", "12.00")],
    "Mains": [("Grilled sea bass", "Fennel, lemon butter, new potatoes", "28.00"),
              ("Ribeye steak", "300g, fries, peppercorn sauce", "36.00"),
              ("Wild mushroom risotto", "Parmesan, truffle oil", "22.00"),
              ("Club sandwich", "Chicken, bacon, egg, fries", "16.00")],
    "Desserts": [("Chocolate fondant", "Vanilla ice cream", "10.00"),
                 ("Lemon tart", "Raspberry sorbet", "9.00")],
    "Drinks": [("Fresh orange juice", "", "5.50"), ("Flat white", "", "4.50"),
               ("House red (glass)", "", "9.00"), ("Sparkling water", "750ml", "4.00")],
}

FIRST_NAMES = ["Olivia", "Liam", "Emma", "Noah", "Ava", "Ethan", "Sophia", "Lucas", "Isabella", "Mason",
               "Aarav", "Zara", "Hiro", "Amara", "Mateo", "Leila", "Kofi", "Ingrid", "Ravi", "Chloe"]
LAST_NAMES = ["Smith", "Garcia", "Patel", "Kim", "Müller", "Silva", "Johnson", "Nguyen", "Brown", "Rossi",
              "Kowalski", "Haddad", "Tanaka", "Mensah", "Dubois", "Andersen", "Singh", "Lopez", "Walker", "Ali"]


class Command(BaseCommand):
    help = "Load demo data: staff, rooms, menu, reservations, orders, invoices, housekeeping and shifts."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing hotel data before loading.")

    def handle(self, *args, reset=False, **options):
        if RoomType.objects.exists() and not reset:
            self.stdout.write(self.style.WARNING("Demo data already present; use --reset to reload it."))
            return
        self.rng = random.Random(42)
        self.today = timezone.localdate()
        with transaction.atomic():
            if reset:
                self._reset()
            self.staff = self._create_staff()
            self._create_rooms()
            self.menu_items = self._create_menu()
            self._create_reservations()
            self._create_walk_in_orders()
            self._create_housekeeping()
            self._create_shifts()
        self.stdout.write(self.style.SUCCESS("Demo data loaded. Staff logins (password: %s):" % PASSWORD))
        for username, first, last, role, _ in STAFF:
            self.stdout.write(f"  {username:<14} {role.label}")

    # helpers -----------------------------------------------------------------
    def _at(self, day, hour_from=8, hour_to=20):
        moment = datetime.combine(day, time(self.rng.randint(hour_from, hour_to), self.rng.randint(0, 59)))
        return timezone.make_aware(moment)

    def _reset(self):
        Invoice.objects.all().delete()
        Order.objects.all().delete()
        HousekeepingTask.objects.all().delete()
        Reservation.objects.all().delete()
        Room.objects.all().delete()
        RoomType.objects.all().delete()
        Amenity.objects.all().delete()
        MenuItem.objects.all().delete()
        MenuCategory.objects.all().delete()
        Shift.objects.all().delete()
        User.objects.filter(username__in=[s[0] for s in STAFF]).delete()

    def _create_staff(self):
        staff = {}
        for username, first, last, role, superuser in STAFF:
            user = User(username=username, first_name=first, last_name=last, role=role,
                        email=f"{username}@grandazure.local", is_superuser=superuser)
            user.set_password(PASSWORD)
            user.save()
            staff[username] = user
        return staff

    def _create_rooms(self):
        amenities = {}
        for spec in ROOM_TYPES:
            room_type = RoomType.objects.create(
                **{k: v for k, v in spec.items() if k not in {"floor", "count", "amenities", "nightly_rate"}},
                nightly_rate=Decimal(spec["nightly_rate"]),
            )
            for name in spec["amenities"]:
                if name not in amenities:
                    amenities[name] = Amenity.objects.create(name=name)
                room_type.amenities.add(amenities[name])
            for i in range(1, spec["count"] + 1):
                Room.objects.create(number=f"{spec['floor']}{i:02d}", floor=spec["floor"], room_type=room_type)

    def _create_menu(self):
        items = []
        for position, (category_name, dishes) in enumerate(MENU.items()):
            category = MenuCategory.objects.create(name=category_name, position=position)
            for name, description, price in dishes:
                items.append(MenuItem.objects.create(category=category, name=name, description=description,
                                                     price=Decimal(price)))
        return items

    def _guest(self):
        first, last = self.rng.choice(FIRST_NAMES), self.rng.choice(LAST_NAMES)
        return {
            "guest_name": f"{first} {last}",
            "guest_email": f"{first}.{last}{self.rng.randint(1, 99)}@example.com".lower().replace("ü", "u"),
            "guest_phone": f"+1 555 {self.rng.randint(100, 999)} {self.rng.randint(1000, 9999)}",
        }

    def _create_order(self, when, *, reservation=None, status=Order.Status.SERVED):
        rng = self.rng
        room_service = reservation is not None and rng.random() < 0.6
        charge = reservation is not None
        order = Order.objects.create(
            order_type=Order.OrderType.ROOM_SERVICE if room_service else Order.OrderType.DINE_IN,
            table_number="" if room_service else str(rng.randint(1, 18)),
            reservation=reservation,
            charge_to_room=charge,
            is_paid=not charge and status == Order.Status.SERVED,
            status=status,
            created_by=self.staff["restaurant"],
        )
        for item in rng.sample(self.menu_items, rng.randint(1, 4)):
            OrderItem.objects.create(order=order, menu_item=item, quantity=rng.randint(1, 3), unit_price=item.price)
        now = timezone.now()
        if when > now:
            when = now - timedelta(minutes=rng.randint(5, 120))
        Order.objects.filter(pk=order.pk).update(created_at=when)
        return order

    # data --------------------------------------------------------------------
    def _create_reservations(self):
        rng, today, S = self.rng, self.today, Reservation.Status
        receptionist = self.staff["reception"]
        self.departed_today = []
        for room in Room.objects.select_related("room_type"):
            day = today - timedelta(days=rng.randint(55, 65))
            while day < today + timedelta(days=40):
                if rng.random() < 0.42:
                    day += timedelta(days=rng.randint(1, 4))
                    continue
                nights = rng.choice([1, 2, 2, 3, 3, 4, 5, 7])
                check_in, check_out = day, day + timedelta(days=nights)
                day = check_out

                if check_out < today or (check_out == today and rng.random() < 0.5):
                    status = rng.choices([S.CHECKED_OUT, S.CANCELLED, S.NO_SHOW], [88, 8, 4])[0]
                elif check_in < today or (check_in == today and rng.random() < 0.5):
                    status = S.CHECKED_IN
                else:
                    status = rng.choices([S.CONFIRMED, S.CANCELLED], [90, 10])[0]

                stayed = status in (S.CHECKED_IN, S.CHECKED_OUT)
                room_type = room.room_type
                source = rng.choices(list(Reservation.Source), [6, 2, 2])[0]
                reservation = Reservation.objects.create(
                    room_type=room_type,
                    room=room if stayed else None,
                    check_in=check_in,
                    check_out=check_out,
                    adults=rng.randint(1, min(2, room_type.capacity)),
                    children=rng.randint(0, room_type.capacity - 2) if room_type.capacity > 2 else 0,
                    nightly_rate=room_type.nightly_rate,
                    status=status,
                    source=source,
                    created_by=receptionist if source != Reservation.Source.ONLINE else None,
                    special_requests=rng.choice(["", "", "", "Late arrival", "Extra pillows", "High floor please"]),
                    checked_in_at=self._at(check_in, 14, 20) if stayed else None,
                    checked_out_at=self._at(check_out, 8, 11) if status == S.CHECKED_OUT else None,
                    cancelled_at=self._at(check_in - timedelta(days=2)) if status == S.CANCELLED else None,
                    **self._guest(),
                )
                booked_on = min(check_in - timedelta(days=rng.randint(0, 30)), today)
                Reservation.objects.filter(pk=reservation.pk).update(created_at=self._at(booked_on))

                if stayed and rng.random() < 0.55:
                    last_day = min(check_out, today)
                    for _ in range(rng.randint(1, 2)):
                        when = self._at(check_in + timedelta(days=rng.randint(0, max((last_day - check_in).days - 1, 0))))
                        in_progress = status == S.CHECKED_IN and when.date() == today
                        self._create_order(
                            when, reservation=reservation,
                            status=rng.choice([Order.Status.PLACED, Order.Status.PREPARING]) if in_progress
                            else Order.Status.SERVED,
                        )

                if status == S.CHECKED_OUT:
                    invoice = build_invoice(reservation)
                    issued = self._at(check_out, 8, 11)
                    if check_out < today - timedelta(days=1) or rng.random() < 0.5:
                        mark_paid(invoice, rng.choice(list(Invoice.PaymentMethod)[:2]))
                        Invoice.objects.filter(pk=invoice.pk).update(issued_at=issued, paid_at=issued)
                    else:
                        Invoice.objects.filter(pk=invoice.pk).update(issued_at=issued)
                    if check_out == today:
                        self.departed_today.append(room.pk)
                elif status == S.CHECKED_IN:
                    room.status = Room.Status.OCCUPIED
                    room.save(update_fields=["status"])

    def _create_walk_in_orders(self):
        for offset in range(45, -1, -1):
            day = self.today - timedelta(days=offset)
            for _ in range(self.rng.randint(2, 6)):
                self._create_order(self._at(day))
        for status in [Order.Status.PLACED, Order.Status.PREPARING, Order.Status.PREPARING]:
            self._create_order(timezone.now() - timedelta(minutes=self.rng.randint(5, 40)), status=status)

    def _create_housekeeping(self):
        rng, today = self.rng, self.today
        cleaners = [self.staff["housekeeping"], self.staff["housekeeping2"]]
        HT = HousekeepingTask

        # Spare rooms per type tonight = free rooms minus guests still to arrive.
        arrivals = Reservation.objects.filter(status=Reservation.Status.CONFIRMED, check_in=today)
        free_by_type = {}
        for room in Room.objects.filter(status=Room.Status.AVAILABLE).select_related("room_type"):
            free_by_type.setdefault(room.room_type_id, []).append(room)
        spare = {type_id: len(rooms) - arrivals.filter(room_type_id=type_id).count()
                 for type_id, rooms in free_by_type.items()}

        def take_spare_room(prefer=()):
            candidates = [r for t, rooms in free_by_type.items() if spare[t] > 1 for r in rooms]
            candidates.sort(key=lambda r: r.pk not in prefer)
            if not candidates:
                return None
            room = candidates[0]
            free_by_type[room.room_type_id].remove(room)
            spare[room.room_type_id] -= 1
            return room

        for _ in range(2):  # rooms vacated this morning waiting for a departure clean
            room = take_spare_room(prefer=self.departed_today)
            if room is None:
                break
            room.status = Room.Status.CLEANING
            room.save(update_fields=["status"])
            HT.objects.create(room=room, priority=HT.Priority.HIGH, assigned_to=rng.choice(cleaners + [None]),
                              notes="Departure clean")

        room = take_spare_room()
        if room:
            room.status = Room.Status.MAINTENANCE
            room.save(update_fields=["status"])
            HT.objects.create(room=room, task_type=HT.TaskType.MAINTENANCE, status=HT.Status.IN_PROGRESS,
                              assigned_to=cleaners[1], notes="Air conditioning not cooling")

        available = list(Room.objects.filter(status=Room.Status.AVAILABLE))
        rng.shuffle(available)
        for room in available[:3]:
            HT.objects.create(room=room, task_type=HT.TaskType.INSPECTION, priority=HT.Priority.LOW,
                              assigned_to=cleaners[0], notes="Weekly inspection")
        for room in rng.sample(list(Room.objects.all()), 8):
            completed = timezone.now() - timedelta(hours=rng.randint(2, 30))
            task = HT.objects.create(room=room, status=HT.Status.DONE, assigned_to=rng.choice(cleaners),
                                     notes="Departure clean", completed_at=completed)
            HT.objects.filter(pk=task.pk).update(created_at=completed - timedelta(hours=1))

    def _create_shifts(self):
        week_start = self.today - timedelta(days=self.today.weekday())
        patterns = [(time(7), time(15)), (time(15), time(23))]
        for username, user in self.staff.items():
            if username == "admin":
                continue
            start, end = patterns[self.rng.randint(0, 1)] if username != "manager" else (time(9), time(17))
            days_off = set(self.rng.sample(range(7), 2))
            for offset in range(14):
                if offset % 7 in days_off:
                    continue
                Shift.objects.create(staff=user, date=week_start + timedelta(days=offset),
                                     start_time=start, end_time=end)
