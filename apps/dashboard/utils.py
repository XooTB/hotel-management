from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import Paginator
from django.db.models import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic.detail import SingleObjectMixin

from apps.accounts.permissions import RoleRequiredMixin


def paginate(request, queryset, per_page=20):
    return Paginator(queryset, per_page).get_page(request.GET.get("page"))


class DashboardFormMixin(RoleRequiredMixin, SuccessMessageMixin):
    """Shared behaviour for dashboard create/update views rendered by dashboard/form.html."""

    template_name = "dashboard/form.html"
    title = ""
    back_url_name = ""
    delete_url_name = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = getattr(self, "object", None)
        context["delete_url"] = reverse(self.delete_url_name, args=[obj.pk]) if obj and self.delete_url_name else None
        context["title"] = self.title or (f"Edit {self.object}" if getattr(self, "object", None) else "Create")
        context["back_url"] = reverse_lazy(self.back_url_name) if self.back_url_name else None
        return context


class DashboardDeleteView(RoleRequiredMixin, SingleObjectMixin, View):
    http_method_names = ["post"]
    success_url_name = ""

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        try:
            obj.delete()
        except ProtectedError:
            messages.error(request, f"{obj} is in use and cannot be deleted.")
        else:
            messages.success(request, f"{obj} deleted.")
        return redirect(self.success_url_name)
