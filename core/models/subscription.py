from datetime import date
from django.db import models
from .base import BaseModel
from .restaurant import Restaurant

class Subscription(BaseModel):
    """
    Subscription model for restaurant plans.
    Inherits common fields from BaseModel.
    """
    class Plan(models.TextChoices):
        STARTER = "STARTER"
        PREMIUM = "PREMIUM"

    plan_name = models.CharField(max_length=100, choices=Plan.choices, default=Plan.STARTER)
    start_date = models.DateField(default=date.today)
    end_date = models.DateField()
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )

    @property
    def is_active(self):
        """
        Check if the subscription is currently active.
        A subscription is active if the current date is between start_date and end_date.
        """
        return self.start_date <= date.today() <= self.end_date

    def save(self, *args, **kwargs):
        """
        Ensure only one active subscription per restaurant at any time.
        """
        if self.start_date and self.end_date:
            overlapping = Subscription.objects.filter(
                restaurant=self.restaurant,
                is_deleted=False,
                end_date__gte=self.start_date,
                start_date__lte=self.end_date
            )
            if self.pk:
                overlapping = overlapping.exclude(pk=self.pk)
            if overlapping.exists():
                raise ValueError("A restaurant cannot have more than one active subscription at a time.")
            if self.end_date <= self.start_date:
                raise ValueError("End date must be after start date.")

        if not self.end_date:
            # If end_date is not set, set it to one year from start_date
            self.end_date = self.start_date.replace(year=self.start_date.year + 1)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.plan_name} ({self.restaurant.name})"
