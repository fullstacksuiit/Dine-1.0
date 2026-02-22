from django.db import models
from enum import Enum
from core.models.base import BaseModel
from core.models.restaurant import Restaurant
from .vendor import Vendor
from .customer import Customer
from .purchase_invoice import PurchaseInvoice


class Payment(BaseModel):
    """Payments made to vendors or received from customers."""

    class PaymentType(Enum):
        VENDOR_PAYMENT = "VENDOR_PAYMENT"
        CUSTOMER_RECEIPT = "CUSTOMER_RECEIPT"

        @classmethod
        def choices(cls):
            return [(tag.value, tag.name.replace("_", " ").title()) for tag in cls]

        @classmethod
        def values(cls):
            return [tag.value for tag in cls]

    class PaymentMode(Enum):
        CASH = "CASH"
        BANK_TRANSFER = "BANK_TRANSFER"
        UPI = "UPI"
        CHEQUE = "CHEQUE"
        OTHER = "OTHER"

        @classmethod
        def choices(cls):
            return [(tag.value, tag.name.replace("_", " ").title()) for tag in cls]

        @classmethod
        def values(cls):
            return [tag.value for tag in cls]

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    payment_type = models.CharField(
        max_length=20,
        choices=PaymentType.choices(),
        db_index=True,
    )
    payment_mode = models.CharField(
        max_length=20,
        choices=PaymentMode.choices(),
        default=PaymentMode.CASH.value,
    )

    # Only one of vendor or customer should be set
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="payments",
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="payments",
    )
    purchase_invoice = models.ForeignKey(
        PurchaseInvoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Cheque number, transaction ID, etc.",
    )
    notes = models.TextField(blank=True, null=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        indexes = [
            models.Index(
                fields=["restaurant", "payment_type", "is_deleted"],
                name="pay_restaurant_type_idx",
            ),
            models.Index(
                fields=["restaurant", "payment_date"],
                name="pay_restaurant_date_idx",
            ),
            models.Index(
                fields=["restaurant", "vendor", "is_deleted"],
                name="pay_restaurant_vendor_idx",
            ),
            models.Index(
                fields=["restaurant", "customer", "is_deleted"],
                name="pay_restaurant_customer_idx",
            ),
        ]

    def __str__(self):
        target = self.vendor.name if self.vendor else (
            self.customer.name if self.customer else "N/A"
        )
        return f"{self.payment_type} | {target} | {self.amount}"

    @classmethod
    def get_payments_for_vendor(cls, vendor_id, restaurant):
        return cls.objects.filter(
            vendor_id=vendor_id, restaurant=restaurant, is_deleted=False
        ).order_by("-payment_date")

    @classmethod
    def get_payments_for_customer(cls, customer_id, restaurant):
        return cls.objects.filter(
            customer_id=customer_id, restaurant=restaurant, is_deleted=False
        ).order_by("-payment_date")
