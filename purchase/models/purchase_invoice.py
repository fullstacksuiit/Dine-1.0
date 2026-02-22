from django.db import models
from enum import Enum
from core.models.base import BaseModel
from core.models.restaurant import Restaurant
from .vendor import Vendor
from .purchase_order import PurchaseOrder


class PurchaseInvoice(BaseModel):
    """Bill/invoice received from a vendor, optionally linked to a PO."""

    class Status(Enum):
        PENDING = "PENDING"
        PARTIALLY_PAID = "PARTIALLY_PAID"
        PAID = "PAID"
        CANCELLED = "CANCELLED"

        @classmethod
        def choices(cls):
            return [(tag.value, tag.name.replace("_", " ").title()) for tag in cls]

        @classmethod
        def values(cls):
            return [tag.value for tag in cls]

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="purchase_invoices",
    )
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name="purchase_invoices",
        db_index=True,
    )
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
    )

    invoice_number = models.CharField(
        max_length=100,
        help_text="Vendor's invoice/bill number",
    )
    invoice_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices(),
        default=Status.PENDING.value,
        db_index=True,
    )

    sub_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cgst = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sgst = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    igst = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    notes = models.TextField(blank=True, null=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Purchase Invoice"
        verbose_name_plural = "Purchase Invoices"
        indexes = [
            models.Index(
                fields=["restaurant", "status", "is_deleted"],
                name="pi_restaurant_status_idx",
            ),
            models.Index(
                fields=["restaurant", "vendor", "is_deleted"],
                name="pi_restaurant_vendor_idx",
            ),
            models.Index(
                fields=["restaurant", "invoice_date"],
                name="pi_restaurant_invdate_idx",
            ),
        ]

    def __str__(self):
        return f"Invoice {self.invoice_number} from {self.vendor.name}"

    @property
    def balance_due(self):
        return self.total_amount - self.amount_paid

    @classmethod
    def get_invoices_for_restaurant(cls, restaurant, status_filter=None):
        qs = cls.objects.filter(restaurant=restaurant, is_deleted=False)
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.select_related("vendor", "purchase_order").order_by("-invoice_date")

    @classmethod
    def get_invoice_by_id(cls, invoice_id, restaurant):
        try:
            return cls.objects.select_related("vendor", "purchase_order").prefetch_related(
                'items', 'items__inventory_item'
            ).get(
                id=invoice_id, restaurant=restaurant, is_deleted=False
            )
        except cls.DoesNotExist:
            return None

    def get_items(self):
        return self.items.filter(is_deleted=False).select_related("inventory_item")
