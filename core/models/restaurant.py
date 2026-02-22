from django.db import models

from datetime import date
from .base import BaseModel


class Restaurant(BaseModel):
    """
    Restaurant model for storing restaurant information.
    Inherits from BaseModel which provides id, timestamps and updated_by fields.
    """
    name = models.CharField(max_length=255, unique=True)
    display_name = models.CharField(
        max_length=255,
        help_text="Name to be displayed to customers/on receipts",
        blank=True,
        null=True
    )
    contact = models.CharField(max_length=20, null=True, blank=True, help_text="Primary contact number")

    # Detailed address fields
    street_address = models.CharField(
        max_length=255,
        help_text="Street address, building name/number",
        blank=True,
        null=True
    )
    locality = models.CharField(
        max_length=100,
        help_text="Locality or area",
        blank=True,
        null=True
    )
    city = models.CharField(
        max_length=100,
        help_text="City or town",
        blank=True,
        null=True
    )
    district = models.CharField(
        max_length=100,
        help_text="District",
        blank=True,
        null=True
    )
    state = models.CharField(
        max_length=100,
        help_text="State or province",
        blank=True,
        null=True
    )
    country = models.CharField(
        max_length=100,
        default="India",
        blank=True,
        null=True
    )
    pincode = models.CharField(
        max_length=10,
        help_text="Postal code",
        blank=True,
        null=True
    )

    gstin = models.CharField(
        max_length=15,
        verbose_name="GSTIN",
        help_text="Goods and Services Tax Identification Number",
        blank=True,
        null=True
    )
    upi_id = models.CharField(
        max_length=255,
        verbose_name="UPI ID",
        help_text="Unified Payment Interface ID for digital payments",
        blank=True,
        null=True
    )
    num_tables = models.PositiveIntegerField(
        default=0,
        help_text="Total number of tables in the restaurant",
    )
    beta_tester = models.BooleanField(default=False)

    def __str__(self):
        return self.display_name if self.display_name else self.name

    @property
    def full_address(self):
        """Returns a formatted full address string"""
        components = []
        if self.street_address:
            components.append(self.street_address)
        if self.locality:
            components.append(self.locality)
        if self.city:
            components.append(self.city)
        if self.district and self.district != self.city:
            components.append(self.district)
        if self.state:
            components.append(self.state)
        if self.country:
            components.append(self.country)
        if self.pincode:
            components.append(f"PIN: {self.pincode}")

        return ", ".join(components) if components else ""

    @property
    def has_active_subscription(self):
        """
        Returns True if the restaurant has at least one active subscription.
        """
        today = date.today()
        return self.subscriptions.filter(
            is_deleted=False,
            start_date__lte=today,
            end_date__gte=today
        ).exists()

    class Meta(BaseModel.Meta):
        verbose_name = "Restaurant"
        verbose_name_plural = "Restaurants"