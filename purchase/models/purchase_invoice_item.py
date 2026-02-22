from django.db import models
from core.models.base import BaseModel
from .purchase_invoice import PurchaseInvoice
from .inventory_item import InventoryItem


class PurchaseInvoiceItem(BaseModel):
    """Line item within a purchase invoice."""

    purchase_invoice = models.ForeignKey(
        PurchaseInvoice,
        on_delete=models.CASCADE,
        related_name="items",
        db_index=True,
    )
    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name="purchase_invoice_items",
    )
    # Snapshot fields
    item_name = models.CharField(max_length=255)
    unit = models.CharField(max_length=20)

    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta(BaseModel.Meta):
        verbose_name = "Purchase Invoice Item"
        verbose_name_plural = "Purchase Invoice Items"

    def __str__(self):
        return f"{self.item_name} x {self.quantity}"
