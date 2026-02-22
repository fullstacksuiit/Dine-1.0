from django.db import models
from core.models.base import BaseModel
from core.models.restaurant import Restaurant


class ExpenseCategory(BaseModel):
    """Categories for tracking expenses (e.g., Utilities, Rent, Ingredients)."""

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="expense_categories",
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Expense Category"
        verbose_name_plural = "Expense Categories"
        unique_together = ("restaurant", "name")
        indexes = [
            models.Index(
                fields=["restaurant", "is_deleted"],
                name="expcat_restaurant_deleted_idx",
            ),
        ]

    def __str__(self):
        return self.name

    @classmethod
    def get_categories_for_restaurant(cls, restaurant):
        return cls.objects.filter(
            restaurant=restaurant, is_deleted=False
        ).order_by("name")

    @classmethod
    def get_or_create_category(cls, name, restaurant):
        category, _ = cls.objects.get_or_create(
            name=name,
            restaurant=restaurant,
            defaults={"is_deleted": False},
        )
        if category.is_deleted:
            category.un_delete()
        return category
