from django.db import models
from core.models.base import BaseModel
from core.models.restaurant import Restaurant


class Vendor(BaseModel):
    """Supplier/Vendor who provides raw materials or goods to the restaurant."""

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="vendors",
    )
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    email = models.EmailField(blank=True, null=True)
    gstin = models.CharField(
        max_length=15,
        verbose_name="GSTIN",
        blank=True,
        null=True,
    )

    # Address
    address_line = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)

    # Bank details
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    bank_account_number = models.CharField(max_length=30, blank=True, null=True)
    bank_ifsc = models.CharField(max_length=11, blank=True, null=True)
    upi_id = models.CharField(max_length=255, blank=True, null=True)

    notes = models.TextField(blank=True, null=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Vendor"
        verbose_name_plural = "Vendors"
        unique_together = ("restaurant", "name")
        indexes = [
            models.Index(
                fields=["restaurant", "is_deleted"],
                name="vendor_restaurant_deleted_idx",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.restaurant})"

    @classmethod
    def get_vendors_for_restaurant(cls, restaurant):
        return cls.objects.filter(
            restaurant=restaurant, is_deleted=False
        ).order_by("name")

    @classmethod
    def get_vendor_by_id(cls, vendor_id, restaurant):
        try:
            return cls.objects.get(
                id=vendor_id, restaurant=restaurant, is_deleted=False
            )
        except cls.DoesNotExist:
            return None
