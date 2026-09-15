from django import forms

from apps.accounts.models import User

from .models import HousekeepingTask


class TaskForm(forms.ModelForm):
    class Meta:
        model = HousekeepingTask
        fields = ["room", "task_type", "priority", "assigned_to", "notes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = User.objects.filter(
            is_active=True, role=User.Role.HOUSEKEEPING
        )
