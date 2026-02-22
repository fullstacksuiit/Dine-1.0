from django.http.response import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from django.shortcuts import render, redirect
from django.db.models import Sum, Avg
from core.models.restaurant import Restaurant
from sale.models import KOT, Bill, Dish
from sale.services import (
    generate_kot,
    organize_menu_by_course,
)
from sale.services.billing_service import BillingService
from sale.services.reporting_service import ReportingService
from sale.services.menu_service import MenuService
from common.decorators import (
    manager_or_above_required,
    waiter_or_above_required,
    subscription_required,
)


# Order Views
@waiter_or_above_required
@subscription_required
@csrf_exempt
@api_view(http_method_names=["GET"])
def order_view(request):
    return render(request, "order.html")


@manager_or_above_required
def bill_form(request):
    return redirect("/")  # Billing now handled within the order page


@manager_or_above_required
def invoice(request, bill_id):
    bill = Bill.objects.select_related('restaurant').filter(id=bill_id, is_deleted=False).first()
    if not bill:
        return HttpResponse("Invalid bill ID or bill not found", status=404)

    grouped_orders = BillingService.group_orders_by_dish_and_size(bill)
    try:
        qr_code = BillingService.generate_payment_qr_code(bill)
    except Exception:
        qr_code = None

    context = {"bill": bill, "orders": grouped_orders, "qr": qr_code}
    return render(request, "invoice.html", context)


@manager_or_above_required
def sale_history(request):
    bills = _get_filtered_completed_bills(request)
    bills = bills.order_by("-updated_at")

    sale = bills.filter(is_deleted=False).aggregate(Avg("amount"), Sum("amount"))
    avg = sale["amount__avg"]
    total_sale = sale["amount__sum"]

    # Group and sum by payment type for the filtered bills only
    totals_by_payment_type = (
        bills.filter(is_deleted=False).values("payment_type")
        .order_by("payment_type")
        .annotate(total_amount=Sum("amount"))
    )

    if avg and total_sale:
        avg = round(avg, 2)
        total_sale = round(total_sale, 2)

    context = {
        "bills": bills,
        "total_sale": total_sale,
        "avg": avg,
        "total_sale_payment_type": totals_by_payment_type,
    }

    return render(request, "billing_history.html", context)


@manager_or_above_required
def report(request):
    bills = _get_filtered_completed_bills(request)
    excel_content, filename = None, None
    if request.POST.get("report_type") == "BILL":
        bills = bills.order_by("updated_at")
        # Use the service function to generate Excel content
        excel_content, filename = ReportingService.generate_excel_response(bills)
    elif request.POST.get("report_type") == "DISH":
        # For dish report, we need to get the dish sales data
        excel_content, filename = ReportingService.generate_dish_summary_report(bills)

    # Create the HTTP response with Excel content
    if not excel_content or not filename:
        return HttpResponse("No data to export", status=400)

    response = HttpResponse(excel_content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@waiter_or_above_required
def menu(request):
    context = {"restaurant": request.restaurant}
    return render(request, "menu.html", context)

def home(request):
    return render(request, "home.html")

@manager_or_above_required
def kot_history(request):
    kots = KOT.get_active_dine_in_KOTs(request.restaurant).order_by("created_at")
    pending_kots = kots.filter(
        accepted=False, status=KOT.Status.PENDING.value
    ).order_by("created_at")
    accepted_kots = (
        kots.exclude(status=KOT.Status.CANCELLED.value)
        .exclude(status=KOT.Status.PENDING.value)
        .order_by("created_at")
    )
    context = {"kots": accepted_kots, "pending_kots": pending_kots}
    return render(request, "kot_history.html", context)


@manager_or_above_required
def settings(request):
    return render(request, "settings.html")


@manager_or_above_required
def kot(request, kot_id):
    return generate_kot(request, kot_id)


@manager_or_above_required
def order_menu(request):
    dishes_qs = Dish.get_dishes_for_restaurant(restaurant=request.restaurant).values()
    dishes = organize_menu_by_course(dishes_qs)
    context = {"map": dishes}
    return render(request, "order_menu.html", context)


def public_menu(request, restaurant_id):
    try:
        restaurant = Restaurant.objects.get(id=restaurant_id, is_deleted=False)
    except (ValueError, Restaurant.DoesNotExist):
        return HttpResponse("Restaurant not found", status=404)
    # Get dishes grouped by course
    dishes = (
        Dish.get_dishes_for_restaurant(restaurant)
        .filter(restaurant_full_price__gt=0)
        .select_related("course")
        .order_by("course__name", "name")
    )
    courses = MenuService.order_dishes(dishes, restaurant)
    context = {
        "restaurant": restaurant,
        "courses": courses,
    }
    return render(request, "public_menu.html", context)


@manager_or_above_required
def takeaway_order_view(request):
    return redirect("/?tab=takeaway")


def order_status_view(request, restaurant_id):
    """
    Public view to render the order_status.html page for a given restaurant.
    """
    return render(request, "order_status.html")


def _get_filtered_completed_bills(request):
    """
    Helper function to get filtered completed bills for a given restaurant.
    """
    if request.method == "POST":
        start_date = request.POST.get("from")
        end_date = request.POST.get("to")
        order_type = request.POST.get("order_type", "ALL")
        payment_type = request.POST.get("payment_type", "ALL")
        bills = ReportingService.get_filtered_invoices(
            start_date, end_date, order_type, payment_type, request.restaurant
        )
    else:
        # Query to get bills of the present day.
        bills = Bill.get_bills_for_today(request.restaurant)

    return bills.filter(active=False, amount__gt=0)  # Include only completed bills
