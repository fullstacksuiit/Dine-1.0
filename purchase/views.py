from django.shortcuts import render
from common.decorators import manager_or_above_required, waiter_or_above_required


@manager_or_above_required
def purchase_dashboard(request):
    return render(request, "purchase/dashboard.html")


@manager_or_above_required
def vendors_view(request):
    return render(request, "purchase/vendors.html")


@waiter_or_above_required
def customers_view(request):
    return render(request, "purchase/customers.html")


@waiter_or_above_required
def inventory_view(request):
    return render(request, "purchase/inventory.html")


@manager_or_above_required
def purchase_orders_view(request):
    return render(request, "purchase/purchase_orders.html")


@manager_or_above_required
def purchase_invoices_view(request):
    return render(request, "purchase/purchase_invoices.html")


@manager_or_above_required
def expenses_view(request):
    return render(request, "purchase/expenses.html")


@manager_or_above_required
def payments_view(request):
    return render(request, "purchase/payments.html")
