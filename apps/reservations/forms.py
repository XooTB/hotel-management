from django import forms

from apps.core_forms import DateInput
from apps.rooms.models import Room, RoomType

from .models import Reservation


class StaffReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = [
            "room_type", "check_in", "check_out", "adults", "children",
            "guest_name", "guest_email", "guest_phone", "source", "special_requests",
        ]
        widgets = {
            "check_in": DateInput,
            "check_out": DateInput,
            "special_requests": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["room_type"].queryset = RoomType.objects.filter(is_active=True)


class CheckInForm(forms.Form):
    room = forms.ModelChoiceField(queryset=Room.objects.none(), empty_label="Select a room")

    def __init__(self, *args, rooms, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["room"].queryset = rooms


class ReservationFilterForm(forms.Form):
    q = forms.CharField(required=False, widget=forms.TextInput(attrs={"placeholder": "Reference, name or email"}))
    status = forms.ChoiceField(choices=[("", "All statuses"), *Reservation.Status.choices], required=False)
    date = forms.DateField(required=False, widget=DateInput, label="Staying on")
