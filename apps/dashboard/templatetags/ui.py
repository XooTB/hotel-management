import hashlib
from decimal import Decimal, InvalidOperation
from functools import lru_cache

from django import template
from django.conf import settings
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

# Lucide-style 24px stroke icons.
ICONS = {
    "home": '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/><path d="M9 21v-6h6v6"/>',
    "calendar": '<rect x="3" y="4.5" width="18" height="17" rx="2"/><path d="M3 9.5h18M8 2.5v4M16 2.5v4"/>',
    "bed": '<path d="M2 20v-8a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v8"/><path d="M2 17h20M6 10V7a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v3"/>',
    "layers": '<path d="m12 3 9 5-9 5-9-5 9-5z"/><path d="m3 13 9 5 9-5"/>',
    "sparkles": '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3z"/><path d="M19 16v4M17 18h4"/>',
    "utensils": '<path d="M4 3v7a3 3 0 0 0 6 0V3M7 3v18"/><path d="M17 21V3c-2.2 1.3-3 4-3 7v3h3"/>',
    "book": '<path d="M4 19.5V5a2 2 0 0 1 2-2h14v16H6a2 2 0 0 0-2 2v-1.5z"/><path d="M8 7h8M8 11h6"/>',
    "receipt": '<path d="M5 2h14v20l-3-2-2 2-2-2-2 2-2-2-3 2V2z"/><path d="M9 7h6M9 11h6M9 15h4"/>',
    "users": '<circle cx="9" cy="8" r="4"/><path d="M2 21a7 7 0 0 1 14 0"/><path d="M16 4a4 4 0 0 1 0 8M22 21a7 7 0 0 0-4-6.3"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "chart": '<path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 5-6"/>',
    "logout": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5M21 12H9"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "x": '<path d="M18 6 6 18M6 6l12 12"/>',
    "arrow-right": '<path d="M5 12h14M13 5l7 7-7 7"/>',
    "arrow-left": '<path d="M19 12H5M11 19l-7-7 7-7"/>',
    "menu": '<path d="M3 6h18M3 12h18M3 18h18"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
    "phone": '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z"/>',
    "printer": '<path d="M6 9V2h12v7"/><rect x="2" y="9" width="20" height="9" rx="2"/><path d="M6 14h12v8H6z"/>',
    "star": '<path d="m12 2 3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1L12 2z"/>',
    "wifi": '<path d="M5 12.5a10 10 0 0 1 14 0M8.5 16a5 5 0 0 1 7 0M2 9a15 15 0 0 1 20 0"/><circle cx="12" cy="19.5" r=".5"/>',
    "map-pin": '<path d="M12 22s7-6.2 7-12a7 7 0 0 0-14 0c0 5.8 7 12 7 12z"/><circle cx="12" cy="10" r="2.5"/>',
    "door": '<path d="M5 21V3h11l3 2v16"/><path d="M3 21h18M13 12h.01"/>',
    "log-in": '<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><path d="m10 17 5-5-5-5M15 12H3"/>',
    "alert": '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
    "wallet": '<path d="M20 7V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h13a2 2 0 0 0 2-2v-2"/><path d="M22 11h-5a2 2 0 0 0 0 4h5v-4z"/>',
    "edit": '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z"/>',
    "trash": '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/>',
}

BADGE_COLORS = {
    "green": "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20",
    "blue": "bg-sky-50 text-sky-700 ring-1 ring-inset ring-sky-600/20",
    "amber": "bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-600/20",
    "red": "bg-rose-50 text-rose-700 ring-1 ring-inset ring-rose-600/20",
    "slate": "bg-slate-100 text-slate-600 ring-1 ring-inset ring-slate-500/20",
    "violet": "bg-violet-50 text-violet-700 ring-1 ring-inset ring-violet-600/20",
}

STATUS_COLORS = {
    # reservations
    "confirmed": "blue", "checked_in": "green", "checked_out": "slate", "cancelled": "red", "no_show": "amber",
    # rooms
    "available": "green", "occupied": "blue", "cleaning": "amber", "maintenance": "red",
    # housekeeping
    "pending": "amber", "in_progress": "blue", "done": "green", "low": "slate", "normal": "blue", "high": "red",
    # restaurant
    "placed": "amber", "preparing": "blue", "served": "green",
    # billing
    "unpaid": "amber", "paid": "green",
    # roles
    "manager": "violet", "receptionist": "blue", "housekeeping": "amber", "restaurant": "green",
}


@register.simple_tag
def icon(name, css="h-5 w-5"):
    paths = ICONS.get(name, ICONS["star"])
    return mark_safe(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" class="{css}" aria-hidden="true">'
        f"{paths}</svg>"
    )


def _hash_asset(path):
    """Short content hash of a file under STATIC_ROOT, or "" if it is missing."""
    try:
        return hashlib.sha256((settings.STATIC_ROOT / path).read_bytes()).hexdigest()[:10]
    except OSError:
        return ""


_cached_hash_asset = lru_cache(maxsize=None)(_hash_asset)


@register.simple_tag
def static_asset(path):
    """URL for a file in static/, fingerprinted so a redeploy is never served stale.

    Django sends these files with a one-day cache header, so the query string is
    what tells the browser that a rebuilt stylesheet is a different file.
    """
    url = f"{settings.STATIC_URL}{path}"
    # Hashed once per process in production; re-read in development so a rebuilt
    # stylesheet shows up without restarting the server.
    fingerprint = _hash_asset(path) if settings.DEBUG else _cached_hash_asset(path)
    return f"{url}?v={fingerprint}" if fingerprint else url


@register.simple_tag
def badge(value, label=None):
    color = BADGE_COLORS[STATUS_COLORS.get(str(value), "slate")]
    return format_html('<span class="badge {}">{}</span>', color, label or value)


@register.simple_tag
def status_dot(value):
    colors = {"green": "bg-emerald-500", "blue": "bg-sky-500", "amber": "bg-amber-500", "red": "bg-rose-500"}
    return format_html('<span class="inline-block h-2 w-2 rounded-full {}"></span>',
                       colors.get(STATUS_COLORS.get(str(value)), "bg-slate-400"))


@register.filter
def money(value):
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return value
    return f"{settings.HOTEL_CURRENCY}{amount:,.2f}"


@register.filter
def get_item(mapping, key):
    return mapping.get(key) if hasattr(mapping, "get") else None


@register.simple_tag(takes_context=True)
def query_transform(context, **kwargs):
    """Current query string with some parameters replaced (for pagination/filter links)."""
    params = context["request"].GET.copy()
    for key, value in kwargs.items():
        if value in (None, ""):
            params.pop(key, None)
        else:
            params[key] = value
    return params.urlencode()


@register.filter
def times(value, arg):
    try:
        return Decimal(str(value)) * Decimal(str(arg))
    except (InvalidOperation, TypeError, ValueError):
        return ""
