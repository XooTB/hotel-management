from django import forms

from .models import Invoice


class PaymentForm(forms.Form):
    payment_method = forms.ChoiceField(choices=Invoice.PaymentMethod.choices)
