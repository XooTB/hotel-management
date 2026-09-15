from django import forms

from .models import Room, RoomType


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ["number", "floor", "room_type", "status", "notes"]


class RoomTypeForm(forms.ModelForm):
    class Meta:
        model = RoomType
        fields = [
            "name", "slug", "short_description", "description", "nightly_rate",
            "capacity", "bed_type", "size_sqm", "amenities", "image", "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "amenities": forms.CheckboxSelectMultiple,
        }
