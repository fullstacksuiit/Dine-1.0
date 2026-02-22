from django.db import models
from enum import Enum
from core.models.base import BaseModel
from core.models.restaurant import Restaurant
from .vendor import Vendor


class PurchaseOrder(BaseModel):
    """Purchase order placed with a vendor."""

    class Status(Enum):
        DRAFT = "DRAFT"
        APPROVED = "APPROVED"
        RECEIVED = "RECEIVED"
        CANCELLED = "CANCELLED"

        @classmethod
        def choices(cls):
            return [(tag.value, tag.name.title()) for tag in cls]

        @classmethod
        def values(cls):
            return [tag.value for tag in cls]

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="purchase_orders",
    )
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name="purchase_orders",
        db_index=True,
    )
    order_number = models.CharField(
        max_length=50,
        help_text="Auto-generated or manual PO number",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices(),
        default=Status.DRAFT.value,
        db_index=True,
    )
    order_date = models.DateField(help_text="Date the PO was raised")
    expected_delivery_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    sub_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta(BaseModel.Meta):
        verbose_name = "Purchase Order"
        verbose_name_plural = "Purchase Orders"
        indexes = [
            models.Index(
                fields=["restaurant", "status", "is_deleted"],
                name="po_restaurant_status_idx",
            ),
            models.Index(
                fields=["restaurant", "vendor", "is_deleted"],
                name="po_restaurant_vendor_idx",
            ),
            models.Index(
                fields=["restaurant", "order_date"],
                name="po_restaurant_orderdate_idx",
            ),
        ]

    def __str__(self):
        return f"PO-{self.order_number} ({self.vendor.name})"

    @classmethod
    def get_orders_for_restaurant(cls, restaurant, status_filter=None):
        qs = cls.objects.filter(restaurant=restaurant, is_deleted=False)
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.select_related("vendor").order_by("-order_date")

    @classmethod
    def get_order_by_id(cls, order_id, restaurant):
        try:
            return cls.objects.select_related("vendor").prefetch_related(
                'items', 'items__inventory_item'
            ).get(
                id=order_id, restaurant=restaurant, is_deleted=False
            )
        except cls.DoesNotExist:
            return None

    def get_items(self):
        return self.items.filter(is_deleted=False).select_related("inventory_item")
