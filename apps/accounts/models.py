from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Hotel staff member. Guests do not have accounts."""

    class Role(models.TextChoices):
        MANAGER = "manager", "Manager"
        RECEPTIONIST = "receptionist", "Receptionist"
        HOUSEKEEPING = "housekeeping", "Housekeeping"
        RESTAURANT = "restaurant", "Restaurant"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.RECEPTIONIST)
    phone = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ["first_name", "last_name", "username"]

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def is_manager(self):
        return self.is_superuser or self.role == self.Role.MANAGER

    def has_role(self, *roles):
        """Managers and superusers implicitly have every role."""
        return self.is_manager or self.role in roles
