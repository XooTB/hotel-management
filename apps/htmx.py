"""HTMX sends these headers on every request it makes."""


def is_htmx(request):
    return request.headers.get("HX-Request") == "true"


def htmx_target(request):
    """Id of the element HTMX will swap the response into."""
    return request.headers.get("HX-Target", "")
