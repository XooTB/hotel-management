from django.db import models
from django.urls import reverse


class Amenity(models.Model):
    name = models.CharField(max_length=60, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "amenities"

    def __str__(self):
        return self.name


class RoomType(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(unique=True)
    short_description = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    nightly_rate = models.DecimalField(max_digits=10, decimal_places=2)
    capacity = models.PositiveSmallIntegerField(default=2)
    bed_type = models.CharField(max_length=60, default="Queen bed")
    size_sqm = models.PositiveSmallIntegerField("size (m²)", default=25)
    amenities = models.ManyToManyField(Amenity, blank=True, related_name="room_types")
    image = models.ImageField(upload_to="room_types/", blank=True)
    is_active = models.BooleanField(default=True, help_text="Inactive types are hidden from the public site.")

    PLACEHOLDER_GRADIENTS = [
        "from-sky-700 to-brand-900",
        "from-amber-600 to-rose-900",
        "from-emerald-600 to-teal-900",
        "from-indigo-600 to-slate-900",
    ]

    class Meta:
        ordering = ["nightly_rate"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("website:room_detail", args=[self.slug])

    @property
    def placeholder_gradient(self):
        """Background used on the public site when no photo has been uploaded."""
        return self.PLACEHOLDER_GRADIENTS[(self.pk or 0) % len(self.PLACEHOLDER_GRADIENTS)]


class Room(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        OCCUPIED = "occupied", "Occupied"
        CLEANING = "cleaning", "Needs cleaning"
        MAINTENANCE = "maintenance", "Maintenance"

    number = models.CharField(max_length=10, unique=True)
    floor = models.SmallIntegerField(default=1)
    room_type = models.ForeignKey(RoomType, on_delete=models.PROTECT, related_name="rooms")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["floor", "number"]

    def __str__(self):
        return f"Room {self.number}"
