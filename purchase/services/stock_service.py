from datetime import date
from decimal import Decimal
from django.db import transaction, models
from purchase.models.inventory_item import InventoryItem
from purchase.models.stock_entry import StockEntry


class StockService:

    @classmethod
    @transaction.atomic
    def add_stock_from_invoice(cls, purchase_invoice, user=None):
        """
        For each PurchaseInvoiceItem, create a PURCHASE_IN StockEntry
        and increment InventoryItem.current_stock.
        Also updates cost_per_unit to latest purchase price.
        """
        entries = []
        for item in purchase_invoice.get_items():
            inv_item = InventoryItem.objects.select_for_update().get(
                id=item.inventory_item_id
            )
            inv_item.current_stock += item.quantity
            inv_item.cost_per_unit = item.unit_price
            inv_item.save(update_fields=["current_stock", "cost_per_unit"])

            entry = StockEntry.objects.create(
                restaurant=purchase_invoice.restaurant,
                inventory_item=inv_item,
                entry_type=StockEntry.EntryType.PURCHASE_IN.value,
                quantity=item.quantity,
                unit_cost=item.unit_price,
                purchase_invoice=purchase_invoice,
                entry_date=purchase_invoice.invoice_date,
                updated_by=user,
            )
            entries.append(entry)
        return entries

    @classmethod
    @transaction.atomic
    def manual_stock_adjustment(
        cls, inventory_item, quantity, entry_type, restaurant, user=None, notes=None
    ):
        """
        Create a manual stock entry and update InventoryItem.current_stock.
        quantity should be positive for additions, negative for removals.
        """
        inv_item = InventoryItem.objects.select_for_update().get(
            id=inventory_item.id
        )

        # For removal types, make quantity negative if it isn't already
        removal_types = [
            StockEntry.EntryType.MANUAL_REMOVE.value,
            StockEntry.EntryType.USAGE.value,
            StockEntry.EntryType.WASTAGE.value,
        ]
        if entry_type in removal_types and quantity > 0:
            quantity = -quantity

        inv_item.current_stock += Decimal(str(quantity))
        inv_item.save(update_fields=["current_stock"])

        entry = StockEntry.objects.create(
            restaurant=restaurant,
            inventory_item=inv_item,
            entry_type=entry_type,
            quantity=quantity,
            unit_cost=inv_item.cost_per_unit,
            entry_date=date.today(),
            notes=notes,
            updated_by=user,
        )
        return entry

    @classmethod
    def get_stock_history(cls, inventory_item, restaurant):
        """Return all stock entries for an item, ordered by date descending."""
        return StockEntry.objects.filter(
            inventory_item=inventory_item,
            restaurant=restaurant,
            is_deleted=False,
        ).order_by("-entry_date", "-created_at")

    @classmethod
    def get_total_stock_value(cls, restaurant):
        """Sum of current_stock * cost_per_unit across all items."""
        result = InventoryItem.objects.filter(
            restaurant=restaurant, is_deleted=False
        ).aggregate(
            total=models.Sum(
                models.F("current_stock") * models.F("cost_per_unit"),
                output_field=models.DecimalField(),
            )
        )
        return result["total"] or Decimal("0.00")
