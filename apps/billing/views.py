from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.permissions import FRONT_DESK, role_required
from apps.dashboard.utils import paginate

from . import services
from .forms import PaymentForm
from .models import Invoice


@role_required(FRONT_DESK)
def invoice_list(request):
    status = request.GET.get("status", "")
    invoices = Invoice.objects.select_related("reservation__room_type").prefetch_related("lines")
    if status in Invoice.Status.values:
        invoices = invoices.filter(status=status)
    context = {"page": paginate(request, invoices), "status": status, "tabs": Invoice.Status.choices}
    return render(request, "billing/list.html", context)


@role_required(FRONT_DESK)
def invoice_detail(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.select_related("reservation__room_type", "reservation__room").prefetch_related("lines"),
        pk=pk,
    )
    return render(request, "billing/detail.html", {"invoice": invoice, "form": PaymentForm()})


@require_POST
@role_required(FRONT_DESK)
def invoice_pay(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, status=Invoice.Status.UNPAID)
    form = PaymentForm(request.POST)
    if form.is_valid():
        services.mark_paid(invoice, form.cleaned_data["payment_method"])
        messages.success(request, f"Invoice {invoice.number} marked as paid.")
    else:
        messages.error(request, "Choose a payment method.")
    return redirect(invoice)
