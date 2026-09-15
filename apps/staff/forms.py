from django import forms
from django.contrib.auth.forms import UserCreationForm

from apps.accounts.models import User
from apps.core_forms import DateInput, TimeInput

from .models import Shift


class StaffCreateForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "first_name", "last_name", "email", "phone", "role"]


class StaffUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "role", "is_active"]


class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = ["staff", "date", "start_time", "end_time", "notes"]
        widgets = {"date": DateInput, "start_time": TimeInput, "end_time": TimeInput}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["staff"].queryset = User.objects.filter(is_active=True)
