from django.db import models
from django.db.models import F
from enum import Enum
from core.models.base import BaseModel
from core.models.restaurant import Restaurant


class InventoryItem(BaseModel):
    """Raw materials, ingredients, or goods tracked in inventory."""

    class Unit(Enum):
        KG = "KG"
        GRAM = "GRAM"
        LITRE = "LITRE"
        ML = "ML"
        PIECE = "PIECE"
        PACKET = "PACKET"
        DOZEN = "DOZEN"
        BOX = "BOX"

        @classmethod
        def choices(cls):
            return [(tag.value, tag.name.title()) for tag in cls]

        @classmethod
        def values(cls):
            return [tag.value for tag in cls]

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="inventory_items",
    )
    name = models.CharField(max_length=255)
    unit = models.CharField(
        max_length=20,
        choices=Unit.choices(),
        default=Unit.KG.value,
    )
    current_stock = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        help_text="Current quantity in stock",
    )
    low_stock_threshold = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
        help_text="Alert when stock falls below this level",
    )
    cost_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Latest cost per unit for valuation",
    )
    category = models.ForeignKey(
        "purchase.ExpenseCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_items",
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Inventory Item"
        verbose_name_plural = "Inventory Items"
        unique_together = ("restaurant", "name")
        indexes = [
            models.Index(
                fields=["restaurant", "is_deleted"],
                name="invitem_restaurant_deleted_idx",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.current_stock} {self.unit})"

    @property
    def is_low_stock(self):
        return self.current_stock <= self.low_stock_threshold

    @property
    def stock_value(self):
        return self.current_stock * self.cost_per_unit

    @classmethod
    def get_items_for_restaurant(cls, restaurant):
        return cls.objects.filter(
            restaurant=restaurant, is_deleted=False
        ).select_related('category').order_by("name")

    @classmethod
    def get_low_stock_items(cls, restaurant):
        return cls.objects.filter(
            restaurant=restaurant,
            is_deleted=False,
            current_stock__lte=F("low_stock_threshold"),
        ).order_by("name")

    @classmethod
    def get_item_by_id(cls, item_id, restaurant):
        try:
            return cls.objects.get(
                id=item_id, restaurant=restaurant, is_deleted=False
            )
        except cls.DoesNotExist:
            return None
