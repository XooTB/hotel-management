from django.urls import reverse

from apps.accounts import permissions as perms

# (label, url name, icon, role group allowed)
NAV_ITEMS = [
    ("Overview", "dashboard:home", "home", perms.ALL_STAFF),
    ("Reservations", "reservations:list", "calendar", perms.FRONT_DESK),
    ("Rooms", "rooms:list", "bed", perms.HOUSEKEEPING),
    ("Room types", "rooms:type_list", "layers", perms.MANAGEMENT),
    ("Housekeeping", "housekeeping:list", "sparkles", perms.HOUSEKEEPING),
    ("Restaurant", "restaurant:order_list", "utensils", perms.RESTAURANT),
    ("Menu", "restaurant:menu", "book", perms.RESTAURANT),
    ("Billing", "billing:list", "receipt", perms.FRONT_DESK),
    ("Staff", "staff:list", "users", perms.MANAGEMENT),
    ("Shifts", "staff:shifts", "clock", perms.ALL_STAFF),
    ("Reports", "dashboard:reports", "chart", perms.MANAGEMENT),
]


def navigation(request):
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated and request.path.startswith("/dashboard/")):
        return {}
    items = [
        {"label": label, "url": reverse(url_name), "icon": icon}
        for label, url_name, icon, roles in NAV_ITEMS
        if perms.user_allowed(user, roles)
    ]
    # The most specific matching URL is the active section.
    matches = [item for item in items if request.path.startswith(item["url"])]
    if matches:
        max(matches, key=lambda item: len(item["url"]))["active"] = True
    return {"nav_items": items}
