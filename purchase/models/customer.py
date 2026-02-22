from django.db import models
from core.models.base import BaseModel
from core.models.restaurant import Restaurant


class Customer(BaseModel):
    """Full customer profile with credit tracking and payment history."""

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="customers",
    )
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, db_index=True)
    email = models.EmailField(blank=True, null=True)
    gstin = models.CharField(
        max_length=15, blank=True, null=True, verbose_name="GSTIN"
    )

    address_line = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)

    credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Maximum credit allowed for this customer",
    )
    opening_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Outstanding balance when customer was added to system",
    )

    notes = models.TextField(blank=True, null=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Customer"
        verbose_name_plural = "Customers"
        unique_together = ("restaurant", "phone")
        indexes = [
            models.Index(
                fields=["restaurant", "is_deleted"],
                name="cust_restaurant_del_idx",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.phone})"

    @classmethod
    def get_customers_for_restaurant(cls, restaurant):
        return cls.objects.filter(
            restaurant=restaurant, is_deleted=False
        ).order_by("name")

    @classmethod
    def get_customer_by_id(cls, customer_id, restaurant):
        try:
            return cls.objects.get(
                id=customer_id, restaurant=restaurant, is_deleted=False
            )
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_customer_by_phone(cls, phone, restaurant):
        try:
            return cls.objects.get(
                phone=phone, restaurant=restaurant, is_deleted=False
            )
        except cls.DoesNotExist:
            return None
