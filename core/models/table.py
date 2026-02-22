from django.db import models

from .base import BaseModel
from .restaurant import Restaurant


class Table(BaseModel):
    """
    Represents a physical table in a restaurant.
    Supports custom names like "Terrace 1", "VIP Room", "Floor 2 - T1".
    The name field is what gets stored in Bill.table_number when an order is placed.
    """

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="tables",
    )
    name = models.CharField(
        max_length=50,
        help_text="Table name/identifier shown on order page",
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Controls the order tables appear in the grid (lower = first)",
    )

    class Meta(BaseModel.Meta):
        unique_together = ("restaurant", "name")
        ordering = ["display_order", "name"]
        verbose_name = "Table"
        verbose_name_plural = "Tables"

    def __str__(self):
        return f"{self.restaurant} - Table {self.name}"

    @classmethod
    def get_tables_for_restaurant(cls, restaurant):
        return cls.objects.filter(
            restaurant=restaurant,
            is_deleted=False,
        ).order_by("display_order", "name")
