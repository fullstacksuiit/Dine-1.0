from enum import Enum
from django.db import models
from core.models.restaurant import Restaurant
from core.models.base import BaseModel
from .dish import Dish
from .bill import Bill
from .kot import KOT


class Order(BaseModel):
    """Model definition for Order."""

    class Size(Enum):
        HALF = "half"
        FULL = "full"

        @classmethod
        def choices(cls):
            """Return choices for the size enum."""
            return [(tag.name, tag.value) for tag in cls]

        @classmethod
        def values(cls):
            """Return values for the size enum."""
            return [tag.value for tag in cls]

        @classmethod
        def is_valid(cls, value):
            return isinstance(value, str) and value in cls.values()

        @classmethod
        def of(cls, value):
            """Return the enum member for a given value."""
            if cls.is_valid(value):
                return cls(value)
            raise ValueError(f"Invalid size value: {value}")

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="orders",
        help_text="Restaurant this order belongs to",
    )
    kot = models.ForeignKey(
        KOT,
        on_delete=models.CASCADE,
        related_name="orders",
        null=True,
        blank=True,
        db_index=True,
    )
    dish = models.ForeignKey(Dish, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField()
    size = models.CharField(
        max_length=50, choices=Size.choices(), default=Size.FULL.value
    )

    # Snapshot of dish details - To be used for display purposes
    dish_name = models.CharField(max_length=150, null=True, blank=True)
    dish_category = models.CharField(max_length=200, null=True, blank=True)
    dish_price = models.FloatField(null=True, blank=True)

    notes = models.CharField(
        max_length=200, blank=True, default="",
        help_text="Special instructions (e.g. extra cheese, no onion, less spicy)",
    )

    bill = models.ForeignKey(
        Bill, related_name="orders", on_delete=models.CASCADE, db_index=True
    )

    class Meta(BaseModel.Meta):
        """Meta definition for Order."""

        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def __str__(self):
        """Unicode representation of Order."""
        return f"{self.kot} | {self.dish_name} ({self.size}) - {self.quantity}"
