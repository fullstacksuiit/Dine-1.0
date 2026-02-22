from django.db import models
from core.models.base import BaseModel
from .purchase_order import PurchaseOrder
from .inventory_item import InventoryItem


class PurchaseOrderItem(BaseModel):
    """Line item within a purchase order."""

    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="items",
        db_index=True,
    )
    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name="purchase_order_items",
    )
    # Snapshot fields (preserved even if inventory_item changes)
    item_name = models.CharField(max_length=255)
    unit = models.CharField(max_length=20)

    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="quantity * unit_price + tax",
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Purchase Order Item"
        verbose_name_plural = "Purchase Order Items"

    def __str__(self):
        return f"{self.item_name} x {self.quantity}"
