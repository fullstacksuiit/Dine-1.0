from django.db import models
from enum import Enum
from core.models.base import BaseModel
from core.models.restaurant import Restaurant
from .inventory_item import InventoryItem
from .purchase_invoice import PurchaseInvoice


class StockEntry(BaseModel):
    """Records individual stock movements (additions, removals, adjustments)."""

    class EntryType(Enum):
        PURCHASE_IN = "PURCHASE_IN"
        MANUAL_ADD = "MANUAL_ADD"
        MANUAL_REMOVE = "MANUAL_REMOVE"
        ADJUSTMENT = "ADJUSTMENT"
        USAGE = "USAGE"
        WASTAGE = "WASTAGE"

        @classmethod
        def choices(cls):
            return [(tag.value, tag.name.replace("_", " ").title()) for tag in cls]

        @classmethod
        def values(cls):
            return [tag.value for tag in cls]

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="stock_entries",
    )
    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name="stock_entries",
        db_index=True,
    )
    entry_type = models.CharField(
        max_length=20,
        choices=EntryType.choices(),
        db_index=True,
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        help_text="Positive for additions, negative for removals",
    )
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Cost per unit at time of entry",
    )
    purchase_invoice = models.ForeignKey(
        PurchaseInvoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_entries",
    )
    notes = models.TextField(blank=True, null=True)
    entry_date = models.DateField(help_text="Date of the stock movement")

    class Meta(BaseModel.Meta):
        verbose_name = "Stock Entry"
        verbose_name_plural = "Stock Entries"
        indexes = [
            models.Index(
                fields=["restaurant", "inventory_item", "is_deleted"],
                name="se_restaurant_item_idx",
            ),
            models.Index(
                fields=["restaurant", "entry_type", "is_deleted"],
                name="se_restaurant_type_idx",
            ),
            models.Index(
                fields=["restaurant", "entry_date"],
                name="se_restaurant_entrydate_idx",
            ),
        ]

    def __str__(self):
        return f"{self.entry_type} | {self.inventory_item.name} | {self.quantity}"
