"""
Services related to order management and processing.
"""

from typing import Optional
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render
from django.contrib.auth.models import User
from sale.models import Order, Dish, KOT
from sale.services.billing_service import BillingService


def create_order(request):
    """Create a new order and associated bill if needed"""
    rp = request.POST
    table = rp.get("table")
    bill = BillingService.initiate_bill(table, request.restaurant, request.user)
    items = rp.getlist("item_id")
    plates = rp.getlist("plate")
    quantities = rp.getlist("quantity")
    dishes = []
    for i in range(len(items)):
        dish = Dish.objects.get(id=items[i])
        data = {
            "bill": bill,
            "dish": dish,
            "quantity": quantities[i],
            "size": plates[i],
            "dish_name": dish.name,  # Snapshot of dish name
            "dish_category": dish.course.name if dish.course else "",  # Snapshot of dish category
            "dish_price": dish.restaurant_full_price if plates[i] == "Full" else dish.restaurant_half_price,  # Snapshot of dish price based on size
            "restaurant": request.restaurant,
            "updated_by": request.user,
        }
        try:
            order_obj = Order.objects.get(dish=dish, bill=bill, size=data["size"])
        except ObjectDoesNotExist:
            order_obj = Order(**data)
        else:
            order_obj.quantity += int(data["quantity"])
        order_obj.save()
        order_data = {
            "dish_name": dish.name,
            "quantity": quantities[i],
            "size": plates[i],
        }
        dishes.append(order_data)
    return bill, dishes


def create_kot(data, bill, updated_by: Optional[User] = None):
    """Create a Kitchen Order Ticket with order details and bill reference"""
    kot = KOT(details=data, bill=bill, restaurant=bill.restaurant, updated_by=updated_by)
    kot.save()
    return kot


def generate_kot(request, kot_id):
    """Generate KOT view based on user role"""
    kot = KOT.objects.get(id=kot_id, restaurant=request.restaurant)
    context = {"kot": kot}
    if request.staff.is_manager or request.staff.is_owner:
        return render(request, "kot.html", context)
    return render(request, "order.html", context)
