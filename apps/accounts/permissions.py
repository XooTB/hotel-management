from functools import wraps

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from .models import User

Role = User.Role

# Role groups allowed into each area. Managers (and superusers) pass every check.
FRONT_DESK = (Role.RECEPTIONIST,)
HOUSEKEEPING = (Role.RECEPTIONIST, Role.HOUSEKEEPING)
RESTAURANT = (Role.RECEPTIONIST, Role.RESTAURANT)
ALL_STAFF = tuple(Role)
MANAGEMENT = ()


def user_allowed(user, roles):
    if not (user.is_authenticated and user.is_active):
        return False
    return user.has_role(*roles)


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restrict a dashboard view to a role group (managers always pass)."""

    allowed_roles = MANAGEMENT

    def test_func(self):
        return user_allowed(self.request.user, self.allowed_roles)


def role_required(roles=MANAGEMENT):
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not user_allowed(request.user, roles):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapper

    return decorator
