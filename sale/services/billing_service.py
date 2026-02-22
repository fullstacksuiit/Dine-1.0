from datetime import datetime
from typing import Optional
from django.db import transaction
from sale.models.bill import Bill
from core.models.restaurant import Restaurant

from django.contrib.auth.models import User

from sale.models.order import Order
from sale.models.kot import KOT
from sale.serializers import OrderSerializer
from sale.services.qr_service import QRService


class BillingService:
    @classmethod
    def get_active_bills(cls, restaurant: Restaurant):
        """
        Get all active bills for a specific restaurant(excluding takeaway bills).
        Returns an empty queryset if no bills exist.
        """
        return Bill.get_active_bills_by_restaurant(restaurant).exclude(is_takeaway=True)

    @classmethod
    def get_active_takeaway_bills(cls, restaurant: Restaurant):
        """
        Get all active takeaway bills for a specific restaurant.
        Returns an empty queryset if no bills exist.
        """
        return Bill.get_active_bills_by_restaurant(restaurant).filter(
            order_type=Bill.OrderType.TAKEAWAY.value
        )

    @classmethod
    def initiate_bill(
        cls,
        table_number: Optional[str],
        restaurant: Restaurant,
        updated_by: Optional[User] = None,
        contact: Optional[str] = None
    ) -> Bill:
        """
        Initiate a new bill for a specific table in a restaurant.
        Returns the created bill instance.
        """

        bill = Bill.get_active_bill_by_table_number(table_number, restaurant)
        if not bill:
            # Create and return the new bill
            bill = Bill.objects.create(
                table_number=table_number, restaurant=restaurant, updated_by=updated_by, contact=contact
            )

        if contact and bill.contact != contact:
            # Update contact if it has changed
            bill.contact = contact
            bill.save(update_fields=["contact"])
        return bill

    @classmethod
    def initiate_takeaway_bill(
        cls, restaurant: Restaurant, updated_by: Optional[User] = None
    ) -> Bill:
        """
        Initiate a new takeaway bill for a restaurant.
        Returns the created bill instance.
        """
        # Create and return the new takeaway bill
        bill = Bill.objects.create(
            restaurant=restaurant,
            updated_by=updated_by,
            is_takeaway=True,
        )
        return bill

    @classmethod
    def update_bill_from_request(cls, bill: Bill, data: dict, updated_by=None):
        """
        Update a Bill instance directly from a dictionary (e.g., request.POST or request.data).
        Returns the updated Bill instance.
        """
        # List of fields to update (add more as needed)
        updatable_fields = [
            "customer_name",
            "contact",
            "order_type",
            "payment_type",
            "sub_total",
            "discount",
            "net",
            "cgst",
            "sgst",
            "igst",
            "amount",
            "delivery_charge",
            "packaging_charge",
            "customer_gstin",
        ]
        for field in updatable_fields:
            if field not in data:
                continue
            value = data[field]
            # Convert empty string to 0 for numeric fields
            if field in [
                "sub_total",
                "discount",
                "net",
                "cgst",
                "sgst",
                "igst",
                "amount",
                "delivery_charge",
                "packaging_charge",
            ]:
                value = float(value) if value not in (None, "") else 0.0
            setattr(bill, field, value)

        cls.update_order_prices(bill)
        # If the bill is a takeaway bill, don't change the active status, it sets to False when all orders are completed
        # We use bill.active for takeaway bills to make sure if it's an update, we don't change the active status
        active = bill.active if bill.is_takeaway else False
        bill.complete_bill(updated_by, active)  # Calls save method
        return bill

    @classmethod
    def update_order_prices(cls, bill):
        """Update prices for each order in the queryset based on order type"""
        # Define price lookup mapping to avoid repetitive if-else blocks
        orders = bill.get_orders().select_related("dish")
        order_type = bill.order_type
        price_mapping = {
            "RESTAURANT": {
                "full": "restaurant_full_price",
                "half": "restaurant_half_price",
            },
            "SWIGGY": {"full": "swiggy_full_price", "half": "swiggy_half_price"},
            "ZOMATO": {"full": "zomato_full_price", "half": "zomato_half_price"},
        }

        # Fetch the relevant mapping once
        order_type_mapping = price_mapping.get(order_type.upper())

        if order_type_mapping:
            for order in orders:
                size = order.size.lower()  # Normalize size to lowercase once
                price_key = order_type_mapping.get(size)
                if price_key:
                    order.dish_price = getattr(order.dish, price_key, None)
            Order.objects.bulk_update(orders, ["dish_price"])  # Batch update orders

    @classmethod
    def generate_payment_qr_code(cls, bill: Bill):
        """
        Generate a payment QR code for the bill.
        This is a placeholder implementation; actual QR code generation logic should be added.
        """
        # Example QR code generation logic (to be replaced with actual implementation)
        if not bill or not hasattr(bill, "amount") or bill.amount is None:
            return None

        if not bill.restaurant.upi_id:
            return None

        # Format the bill amount with 2 decimal places
        amount = f"{bill.amount:.2f}"

        # Format the bill ID with a shorter representation for the QR code
        # Use the first 8 characters of the UUID string to keep it readable
        bill_id_str = str(bill.id)[:4]

        # Create a descriptive note for the payment
        note = f"Bill: {bill_id_str}, Table: {bill.table_number or 'N/A'}"

        return QRService.generate_qr_code_for_payment(
            amount=amount, note=note, upi_id=bill.restaurant.upi_id
        )

    @classmethod
    def group_orders_by_dish_and_size(cls, bill):
        """
        Group orders by dish and size, returning a dictionary with dish names as keys
        and a list of dictionaries containing size and quantity as values.
        """
        orders_qs = bill.get_orders()
        grouped = {}
        for order in orders_qs:
            key = (order.dish_id, order.size)
            if key not in grouped:
                grouped[key] = {
                    "order": order,
                    "quantity": 0,
                    "dish_price": order.dish_price or 0.0,
                }
            grouped[key]["quantity"] += order.quantity

        grouped_orders = []
        for group in grouped.values():
            order_data = dict(OrderSerializer(group["order"]).data)
            order_data["quantity"] = group["quantity"]
            order_data["dish_price"] = group["dish_price"]
            grouped_orders.append(order_data)
        return grouped_orders

    @classmethod
    @transaction.atomic
    def merge_tables(cls, source_bill: Bill, target_bill: Bill, user=None):
        """
        Merge all orders and KOTs from source_bill into target_bill.
        The source bill is deactivated and soft-deleted after the merge.
        Returns the number of orders transferred.
        """
        if source_bill.id == target_bill.id:
            raise ValueError("Cannot merge a table into itself.")
        if not source_bill.active or not target_bill.active:
            raise ValueError("Both tables must be active to merge.")
        if source_bill.restaurant_id != target_bill.restaurant_id:
            raise ValueError("Cannot merge tables from different restaurants.")

        # Move all non-deleted orders from source to target
        orders_transferred = Order.objects.filter(
            bill=source_bill, is_deleted=False
        ).update(bill=target_bill)

        # Move all non-deleted KOTs from source to target
        KOT.objects.filter(
            bill=source_bill, is_deleted=False
        ).update(bill=target_bill)

        # Deactivate and soft-delete the source bill
        source_bill.active = False
        source_bill.is_deleted = True
        source_bill.updated_by = user
        source_bill.save(update_fields=["active", "is_deleted", "updated_by"])

        return orders_transferred
