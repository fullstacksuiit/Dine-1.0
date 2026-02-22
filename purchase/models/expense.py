from django.db import models
from core.models.base import BaseModel
from core.models.restaurant import Restaurant
from .expense_category import ExpenseCategory
from .vendor import Vendor
from .payment import Payment


class Expense(BaseModel):
    """General expense record (rent, utilities, supplies, etc.)."""

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="expenses",
    )
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
        db_index=True,
    )
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
    )

    description = models.CharField(max_length=500)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField(db_index=True)

    payment_mode = models.CharField(
        max_length=20,
        choices=Payment.PaymentMode.choices(),
        default=Payment.PaymentMode.CASH.value,
    )
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"
        indexes = [
            models.Index(
                fields=["restaurant", "is_deleted"],
                name="expense_restaurant_deleted_idx",
            ),
            models.Index(
                fields=["restaurant", "category", "is_deleted"],
                name="expense_restaurant_cat_idx",
            ),
            models.Index(
                fields=["restaurant", "expense_date"],
                name="expense_restaurant_date_idx",
            ),
        ]

    def __str__(self):
        return f"{self.description} - {self.amount}"

    @classmethod
    def get_expenses_for_restaurant(cls, restaurant, category=None):
        qs = cls.objects.filter(restaurant=restaurant, is_deleted=False)
        if category:
            qs = qs.filter(category=category)
        return qs.select_related("category", "vendor").order_by("-expense_date")
