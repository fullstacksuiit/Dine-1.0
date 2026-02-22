from datetime import datetime
from uuid import UUID
from django.db import models
from core.models.base import BaseModel
from core.models.restaurant import Restaurant
from enum import Enum


class Bill(BaseModel):
    """Model definition for Bill."""

    class OrderType(Enum):
        RESTAURANT = "RESTAURANT"
        ZOMATO = "ZOMATO"
        SWIGGY = "SWIGGY"
        TAKEAWAY = "TAKEAWAY"

    class PaymentStatus(Enum):
        UNPAID = "UNPAID"
        PAID = "PAID"

    invoice_number = models.PositiveBigIntegerField(
        editable=False,
        help_text="Unique invoice number for the bill for the current financial year",
        null=True,
        blank=True,
    )

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="bills",
        help_text="Restaurant this bill belongs to",
    )
    discount = models.FloatField(default=0.0)
    sub_total = models.FloatField(default=0.0)
    net = models.FloatField(default=0.0)
    delivery_charge = models.FloatField(default=0.0)
    packaging_charge = models.FloatField(default=0.0)
    amount = models.FloatField(default=0.0)

    cgst = models.FloatField(default=0.0)
    sgst = models.FloatField(default=0.0)
    igst = models.FloatField(default=0.0)

    payment_type = models.CharField(max_length=50, default="Cash", db_index=True)
    order_type = models.CharField(
        max_length=50,
        choices=[(tag.value, tag.name.title()) for tag in OrderType],
        default=OrderType.RESTAURANT.value,
        db_index=True,
    )
    table_number = models.CharField(null=True, max_length=50, blank=True, db_index=True)

    customer_name = models.CharField(max_length=100, null=True, blank=True)
    contact = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    customer_gstin = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="GSTIN of the customer, if provided.",
    )
    customer = models.ForeignKey(
        "purchase.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bills",
    )

    payment_status = models.CharField(
        max_length=10,
        choices=[(tag.value, tag.name.title()) for tag in PaymentStatus],
        default=PaymentStatus.UNPAID.value,
        db_index=True,
    )

    active = models.BooleanField(default=True, db_index=True)
    is_takeaway = models.BooleanField(default=False, help_text="Indicates if this bill is for a takeaway order.")
    is_edited = models.BooleanField(default=False, help_text="Indicates if this bill was edited after creation.")

    class Meta(BaseModel.Meta):
        """Meta definition for Bill."""

        verbose_name = "Bill"
        verbose_name_plural = "Bills"
        indexes = [
            models.Index(
                fields=["restaurant", "created_at", ],
                name="bill_restaurant_createdat_idx",
            ),
            models.Index(
                fields=["restaurant", "active", "is_deleted"],
                name="bill_restaurant_active_idx",
            ),
            models.Index(
                fields=["restaurant", "is_takeaway", "is_deleted"],
                name="bill_restaurant_takeaway_idx",
            ),
            models.Index(
                fields=["restaurant", "payment_status", "is_deleted"],
                name="bill_restaurant_paystatus_idx",
            ),
        ]

    def _get_next_invoice_number(self):
        """
        Returns the next invoice number for this restaurant and current financial year.
        Ensures the number is not already used (handles rare race conditions).
        """
        now = datetime.now()
        if now.month >= 4:
            fiscal_year_start = now.replace(month=4, day=1)
        else:
            fiscal_year_start = now.replace(year=now.year - 1, month=4, day=1)
        fiscal_year_end = fiscal_year_start.replace(year=fiscal_year_start.year + 1, month=3, day=31)
        qs = Bill.objects.filter(
            restaurant=self.restaurant,
            created_at__gte=fiscal_year_start,
            created_at__lte=fiscal_year_end,
            invoice_number__isnull=False,
        )
        max_invoice = (
            qs.aggregate(models.Max("invoice_number"))["invoice_number__max"] or 0
        )
        # Ensure uniqueness in case of race condition
        next_invoice = max_invoice + 1
        while qs.filter(invoice_number=next_invoice).exists():
            next_invoice += 1
        return next_invoice

    def complete_bill(self, updated_by=None, active=False):
        """
        Mark the bill as complete by setting active to False.
        This indicates that the bill is no longer active.
        Also sets the invoice_number for the current financial year and restaurant.
        Ensures no duplicate invoice number.
        """
        if not self.invoice_number:
            self.invoice_number = self._get_next_invoice_number()
        self.active = active
        self.updated_by = updated_by
        self.save()

    def update_payment_mode(self, payment_type):
        """
        Update the payment mode for the bill.
        This allows changing the payment type after the bill has been created.
        """
        self.payment_type = payment_type
        self.save(update_fields=["payment_type"])

    def settle_bill(self, payment_type, updated_by=None):
        """
        Mark the bill as paid with the given payment type.
        """
        self.payment_status = self.PaymentStatus.PAID.value
        self.payment_type = payment_type
        self.updated_by = updated_by
        self.save(update_fields=["payment_status", "payment_type", "updated_by"])

    def get_orders(self):
        return self.orders.filter(is_deleted=False).select_related('dish', 'dish__course')

    @classmethod
    def get_active_bills_by_restaurant(cls, restaurant):
        """
        Get all bills for a specific restaurant.
        Returns an empty queryset if no bills exist.
        """
        return cls.objects.filter(restaurant=restaurant, is_deleted=False, active=True)

    @classmethod
    def get_active_bill_by_table_number(cls, table_number, restaurant):
        """
        Retrieve a bill by table number within a specific restaurant.
        Returns None if no bill is found.
        """
        try:
            return cls.objects.get(
                table_number=table_number,
                restaurant=restaurant,
                is_deleted=False,
                active=True,
            )
        except cls.DoesNotExist:
            return None

    @classmethod
    def is_table_occupied(cls, table_number, restaurant):
        """
        Check if a table is currently occupied by an open bill.
        Check only within that restaurant.
        """
        return cls.objects.filter(
            table_number=table_number,
            restaurant=restaurant,
            active=True,
            is_deleted=False,
        ).exists()

    @classmethod
    def get_bill_by_id(cls, bill_id: UUID, restaurant: Restaurant):
        """
        Retrieve a bill by its ID.
        Returns None if no bill is found.
        """
        try:
            return cls.objects.get(id=bill_id, restaurant=restaurant, is_deleted=False)
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_bills_for_today(cls, restaurant):
        """
        Get all bills created today for a specific restaurant.
        Returns an empty queryset if no bills exist.
        """
        return cls.objects.filter(
            created_at__date=datetime.now().date(), restaurant=restaurant
        )

    def soft_delete(self, updated_by=None):
        super().soft_delete(updated_by)
        # Soft delete related KOTs
        from .kot import KOT  # To avoid circular import

        KOT.objects.filter(bill=self, is_deleted=False).update(
            is_deleted=True, updated_by=updated_by
        )
        # Soft delete related Orders
        from .order import Order  # To avoid circular import

        Order.objects.filter(bill=self, is_deleted=False).update(
            is_deleted=True, updated_by=updated_by
        )

    @classmethod
    def get_bills_for_customer(cls, contact, restaurant):
        """
        Get all bills for a specific customer contact number at a restaurant.
        Returns an empty queryset if no bills exist.
        """
        return cls.objects.filter(
            contact=contact,
            restaurant=restaurant,
            is_deleted=False,
            active=False  # Only completed bills
        )

    def __str__(self):
        """Unicode representation of Bill."""
        return f"{self.restaurant.display_name} - Bill {self.invoice_number} : Table {self.table_number or 'N/A'}"

    @property
    def full_invoice_number(self):
        """
        Return the invoice number as financial year/invoice_number, e.g. 25-26/123.
        """
        created = self.created_at
        year = created.year
        if created.month >= 4:
            start_year = year % 100
            end_year = (year + 1) % 100
        else:
            start_year = (year - 1) % 100
            end_year = year % 100
        return f"{start_year:02d}-{end_year:02d}/{self.invoice_number}"
