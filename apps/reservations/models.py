import secrets

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

REFERENCE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I confusion


def generate_reference():
    return "GA" + "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(6))


class Reservation(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"
        CHECKED_IN = "checked_in", "Checked in"
        CHECKED_OUT = "checked_out", "Checked out"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No-show"

    class Source(models.TextChoices):
        ONLINE = "online", "Online"
        WALK_IN = "walk_in", "Walk-in"
        PHONE = "phone", "Phone"

    # Statuses that hold inventory (block a room for the stay dates).
    ACTIVE_STATUSES = (Status.CONFIRMED, Status.CHECKED_IN)

    reference = models.CharField(max_length=12, unique=True, editable=False)
    room_type = models.ForeignKey("rooms.RoomType", on_delete=models.PROTECT, related_name="reservations")
    room = models.ForeignKey(
        "rooms.Room", on_delete=models.SET_NULL, null=True, blank=True, related_name="reservations"
    )
    guest_name = models.CharField(max_length=120)
    guest_email = models.EmailField()
    guest_phone = models.CharField(max_length=30)
    check_in = models.DateField()
    check_out = models.DateField()
    adults = models.PositiveSmallIntegerField(default=1)
    children = models.PositiveSmallIntegerField(default=0)
    nightly_rate = models.DecimalField(max_digits=10, decimal_places=2)
    special_requests = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.ONLINE)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(check_out__gt=models.F("check_in")),
                name="reservation_check_out_after_check_in",
            )
        ]
        indexes = [models.Index(fields=["check_in", "check_out", "status"])]

    def __str__(self):
        return f"{self.reference} – {self.guest_name}"

    def get_absolute_url(self):
        return reverse("reservations:detail", args=[self.reference])

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = generate_reference()
            while Reservation.objects.filter(reference=self.reference).exists():
                self.reference = generate_reference()
        super().save(*args, **kwargs)

    @property
    def nights(self):
        return (self.check_out - self.check_in).days

    @property
    def guests(self):
        return self.adults + self.children

    @property
    def room_total(self):
        return self.nightly_rate * self.nights

    @property
    def can_cancel(self):
        return self.status == self.Status.CONFIRMED and self.check_in >= timezone.localdate()

    @property
    def can_check_in(self):
        return self.status == self.Status.CONFIRMED and self.check_in <= timezone.localdate()

    @property
    def can_check_out(self):
        return self.status == self.Status.CHECKED_IN

    @property
    def can_mark_no_show(self):
        return self.status == self.Status.CONFIRMED and self.check_in <= timezone.localdate()
