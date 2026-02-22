from typing import Optional
from django.db import models
from django.utils import timezone
from core.models.base import BaseModel
from core.models.restaurant import Restaurant
from core.models.staff import Staff
from .bill import Bill
from enum import Enum


class KOT(BaseModel):
    """Model definition for Kitchen Order Ticket."""

    class Status(Enum):
        PENDING = "Pending"
        IN_PROGRESS = "In Progress"
        READY = "Ready"
        COMPLETED = "Completed"
        CANCELLED = "Cancelled"

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
        related_name="kots",
        help_text="Restaurant this KOT belongs to",
    )
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, db_index=True, related_name="kots")
    details = models.JSONField(default=list)
    accepted = models.BooleanField(default=False)
    status = models.CharField(
        max_length=50,
        choices=Status.choices(),
        default=Status.PENDING.value,
    )
    created_by = models.ForeignKey(
        Staff,
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        related_name="created_kots",
    )
    kot_number = models.PositiveIntegerField(
        editable=False,
        help_text="Serial KOT number for the restaurant, resets every day",
        null=True,
        blank=True,
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Kitchen Order Ticket"
        verbose_name_plural = "Kitchen Order Tickets"
        indexes = [
            models.Index(fields=["restaurant", "status"], name="kot_bill_status_idx"),
        ]

    def accept(self):
        """
        Accept the KOT by setting accepted to True.
        This indicates that the KOT has been acknowledged.
        """
        self.accepted = True
        self.status = self.Status.IN_PROGRESS.value
        self.save(update_fields=["accepted", "status"])

    def update_details(self, details: list, updated_by: Optional[Staff] = None):
        """
        Update the details of the KOT.
        This is useful for adding or modifying items in the KOT.
        """
        self.details = details
        self.updated_by = updated_by
        self.save()

    @classmethod
    def get_active_dine_in_KOTs(cls, restaurant):
        """
        Get all active Dine In KOTs for a given restaurant.
        Active KOTs are those that are not soft deleted and have active True.
        """
        return cls.objects.select_related('bill').filter(
            restaurant=restaurant, is_deleted=False, bill__active=True, bill__is_takeaway=False
        )

    @classmethod
    def get_active_takeaway_KOTs(cls, restaurant):
        """
        Get all active takeaway KOTs for a given restaurant.
        Active takeaway KOTs are those that are not soft deleted and have active True.
        """
        return cls.objects.select_related('bill').filter(
            restaurant=restaurant, is_deleted=False, bill__active=True, bill__is_takeaway=True, bill__amount__gt=0
        )

    @classmethod
    def get_kot_by_id(cls, kot_id, restaurant):
        """
        Get a specific KOT by its ID and restaurant.
        Returns the KOT instance if found, otherwise raises an exception.
        """
        return cls.objects.get(id=kot_id, restaurant=restaurant, is_deleted=False)

    # In-memory cache for KOT numbers: {(restaurant_id, date): max_kot_number}
    _kot_counter_cache = {}

    def _get_next_kot_number(self):
        """
        Returns the next KOT number for this restaurant for today.
        Uses in-memory cache to minimize DB aggregation.
        """
        today = timezone.now().date()
        key = (self.restaurant.id, today)

        # Check cache first
        if key in self._kot_counter_cache:
            next_kot = self._kot_counter_cache[key] + 1
            self._kot_counter_cache[key] = next_kot
            return next_kot

        # Fallback to DB if not in cache (first run of the day/restart)
        qs = KOT.objects.filter(restaurant=self.restaurant, created_at__date=today)
        max_kot = qs.aggregate(models.Max("kot_number"))["kot_number__max"] or 0

        # Hydrate cache
        self._kot_counter_cache[key] = max_kot

        next_kot = max_kot + 1

        # Double check uniqueness in DB (paranoid check against race conditions on cold start)
        while qs.filter(kot_number=next_kot).exists():
             next_kot += 1

        # Update cache
        self._kot_counter_cache[key] = next_kot
        return next_kot

    def cancel(self, updated_by: Optional[Staff] = None):
        """
        Cancel the KOT by setting its status to CANCELLED.
        This indicates that the KOT is no longer valid.
        """
        from sale.models.order import Order # To avoid circular import issues

        self.status = self.Status.CANCELLED.value
        self.updated_by = updated_by
        self.save(update_fields=["status", "updated_by"])

        Order.objects.filter(kot=self).update(
            is_deleted=True, updated_by=updated_by
        )

    @property
    def is_completed(self) -> bool:
        """
        Check if the KOT is completed.
        A KOT is considered completed if its status is COMPLETED.
        """
        return self.status == self.Status.COMPLETED.value

    def save(self, *args, **kwargs):
        if self.kot_number is None:
            self.kot_number = self._get_next_kot_number()

        # Update cache if we are saving a new highest number (e.g. manual override or sync)
        if self.created_at:
             today = self.created_at.date()
        else:
             today = timezone.now().date()

        key = (self.restaurant.id, today)
        current_max = self._kot_counter_cache.get(key, 0)
        if self.kot_number > current_max:
             self._kot_counter_cache[key] = self.kot_number

        if self.bill.is_takeaway and self.status == self.Status.PENDING.value:
            self.status = self.Status.IN_PROGRESS.value
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"KOT #{self.kot_number} | Table - {self.bill.table_number or 'N/A'} | Status - {self.status} | Restaurant - {self.restaurant.display_name}"
