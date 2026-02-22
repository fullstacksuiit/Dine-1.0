from django.contrib.auth.models import User
from django.db import transaction
from sale.services.billing_service import BillingService

from typing import Optional
from sale.models.bill import Bill
from sale.models.kot import KOT
from sale.models.order import Order
from sale.models.dish import Dish


class OrderingService:
    @classmethod
    def initiate_kot(cls, bill: Bill, updated_by: Optional[User] = None):
        return cls.create_kot(bill, details=[], updated_by=updated_by)

    @classmethod
    def create_kot(cls, bill: Bill, details: list, updated_by: Optional[User] = None):
        kot = KOT(
            bill=bill,
            restaurant=bill.restaurant,
            updated_by=updated_by,
            details=details,
        )
        kot.save()
        return kot

    @classmethod
    def create_order(
        cls,
        kot: KOT,
        dish: Dish,
        quantity: int,
        size: Order.Size,
        updated_by: Optional[User] = None,
    ):
        order = Order(
            kot=kot,
            dish=dish,
            quantity=quantity,
            size=size.value,
            dish_name=dish.name,
            dish_category=dish.course.name if dish.course else "",
            dish_price=None,  # To be set based on the platform later when creating the bill
            restaurant=kot.restaurant,
            updated_by=updated_by,
            bill=kot.bill,
        )
        order.save()
        return order

    @classmethod
    def create_order_flow(cls, restaurant, user, data):
        """
        Orchestrates the entire order creation flow atomically.
        1. Initiates/Gets Bill
        2. Prepares Orders and Details
        3. Creates KOT (single save)
        4. Bulk creates Orders
        """
        is_takeaway = data.get("is_takeaway", False)
        table = data.get("table")

        with transaction.atomic():
            if is_takeaway:
                bill = BillingService.initiate_takeaway_bill(restaurant, user)
            else:
                if not table:
                    # Should be handled by validation in API, but safety check
                    raise ValueError("Table number is required for dine-in orders")
                contact = data.get("contact")
                bill = BillingService.initiate_bill(table, restaurant, user, contact=contact)

            items = data.get("items", [])
            sizes = data.get("sizes", [])
            quantities = data.get("quantities", [])
            notes_list = data.get("notes", [])

            # Prepare everything in memory first
            details, orders_to_create = cls._prepare_orders_and_details(
                restaurant, user, items, sizes, quantities, bill, notes_list
            )

            # Create KOT with calculated details (Single Save)
            kot = KOT(
                bill=bill,
                restaurant=restaurant,
                updated_by=user,
                details=details
            )
            kot.save()

            # Assign KOT to orders
            for order in orders_to_create:
                order.kot = kot

            # Bulk create orders
            if orders_to_create:
                Order.objects.bulk_create(orders_to_create)

            return kot, details

    @classmethod
    def process_orders_from_request(cls, restaurant, user, items, sizes, quantities, kot):
        """
        Legacy method kept for compatibility, delegating to _prepare_orders_and_details
        and then saving.
        """
        details, orders_to_create = cls._prepare_orders_and_details(
            restaurant, user, items, sizes, quantities, kot.bill
        )
        # Assign kot and save
        for order in orders_to_create:
             order.kot = kot

        if orders_to_create:
            Order.objects.bulk_create(orders_to_create)

        return details

    @classmethod
    def _prepare_orders_and_details(cls, restaurant, user, items, sizes, quantities, bill, notes_list=None):
        """
        Helper to calculate details and prepare Order objects (without KOT assigned yet).
        """
        notes_list = notes_list or []
        details = []
        orders_to_create = []

        # Bulk fetch dishes
        dishes = Dish.objects.filter(
            id__in=items, restaurant=restaurant, is_deleted=False
        ).select_related("course")

        dish_map = {str(dish.id): dish for dish in dishes}

        # Prepare price mapping logic
        order_type = bill.order_type
        price_mapping = {
            "RESTAURANT": {
                "full": "restaurant_full_price",
                "half": "restaurant_half_price",
            },
            "SWIGGY": {"full": "swiggy_full_price", "half": "swiggy_half_price"},
            "ZOMATO": {"full": "zomato_full_price", "half": "zomato_half_price"},
        }
        order_type_mapping = price_mapping.get(order_type.upper())

        for i in range(len(items)):
            dish_id = items[i]
            dish = dish_map.get(dish_id)

            if not dish:
                continue

            size_val = sizes[i]
            if not Order.Size.is_valid(size_val):
                 size_enum = Order.Size.of(size_val)
            else:
                 size_enum = Order.Size(size_val)

            quantity = int(quantities[i])

            # Determine Price
            dish_price = None
            if order_type_mapping:
                 price_key = order_type_mapping.get(size_enum.value.lower())
                 if price_key:
                     dish_price = getattr(dish, price_key, None)

            note = notes_list[i].strip() if i < len(notes_list) and notes_list[i] else ""

            # Prepare Order object (in-memory)
            # KOT is NOT assigned here yet
            order = Order(
                kot=None, # To be assigned later
                dish=dish,
                quantity=quantity,
                size=size_enum.value,
                dish_name=dish.name,
                dish_category=dish.course.name if dish.course else "",
                dish_price=dish_price,
                notes=note,
                restaurant=restaurant,
                updated_by=user,
                bill=bill,
            )
            orders_to_create.append(order)

            detail = {
                "dish": order.dish_name,
                "quantity": order.quantity,
                "size": order.size,
            }
            if note:
                detail["notes"] = note
            details.append(detail)
        return details, orders_to_create
