from datetime import timedelta

from django import forms
from django.utils import timezone

from apps.core_forms import DateInput
from apps.reservations.services import BookingError, validate_stay


class StayDatesMixin:
    def clean(self):
        cleaned = super().clean()
        check_in, check_out = cleaned.get("check_in"), cleaned.get("check_out")
        if check_in and check_out:
            try:
                validate_stay(check_in, check_out)
            except BookingError as exc:
                raise forms.ValidationError(str(exc)) from exc
        return cleaned


class AvailabilityForm(StayDatesMixin, forms.Form):
    check_in = forms.DateField(widget=DateInput)
    check_out = forms.DateField(widget=DateInput)
    guests = forms.IntegerField(min_value=1, max_value=8, initial=2)

    @classmethod
    def with_defaults(cls, data=None):
        today = timezone.localdate()
        initial = {"check_in": today, "check_out": today + timedelta(days=1), "guests": 2}
        return cls(data or None, initial=initial)


class BookingForm(StayDatesMixin, forms.Form):
    check_in = forms.DateField(widget=forms.HiddenInput)
    check_out = forms.DateField(widget=forms.HiddenInput)
    guest_name = forms.CharField(label="Full name", max_length=120)
    guest_email = forms.EmailField(label="Email")
    guest_phone = forms.CharField(label="Phone", max_length=30)
    adults = forms.IntegerField(min_value=1, max_value=8, initial=2)
    children = forms.IntegerField(min_value=0, max_value=8, initial=0)
    special_requests = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)

    def __init__(self, *args, room_type, **kwargs):
        self.room_type = room_type
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        guests = (cleaned.get("adults") or 0) + (cleaned.get("children") or 0)
        if guests > self.room_type.capacity:
            raise forms.ValidationError(f"{self.room_type.name} sleeps up to {self.room_type.capacity} guests.")
        return cleaned


class LookupForm(forms.Form):
    reference = forms.CharField(label="Booking reference", max_length=12)
    email = forms.EmailField()

    def clean_reference(self):
        return self.cleaned_data["reference"].strip().upper()
