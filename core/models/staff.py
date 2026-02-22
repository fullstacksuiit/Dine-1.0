from django.db import models
from django.conf import settings

from enum import Enum

from .base import BaseModel
from .restaurant import Restaurant


class Role(Enum):
    OWNER = "OWNER"
    MANAGER = "MANAGER"
    WAITER = "WAITER"


class Staff(BaseModel):
    """
    Staff model for restaurant employees.
    Links Django User model with Restaurant and defines staff roles.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='staff_profiles',
        help_text="User account associated with this staff member"
    )

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='staff',
        help_text="Restaurant where this staff member works"
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Contact phone number"
    )

    join_date = models.DateField(
        auto_now_add=True,
        help_text="Date when staff member joined"
    )

    class Meta(BaseModel.Meta):
        # Inherits from BaseModel.Meta (abstract=True), this is safe in Django
        verbose_name = "Staff Member"
        verbose_name_plural = "Staff"
        unique_together = ['user', 'restaurant']  # A user can't have multiple roles at the same restaurant
        ordering = ['restaurant', 'user__first_name']

    def __str__(self):
        return f"{self.user} at {self.restaurant.name}"  # type: ignore

    @classmethod
    def get_staff_by_restaurant(cls, restaurant):
        """
        Get all staff records for a given restaurant.
        Returns an empty queryset if no staff records exist for the restaurant.
        """
        return cls.objects.filter(
            restaurant=restaurant, is_deleted=False
        ).select_related('user').prefetch_related('user__groups')

    @classmethod
    def get_staff_by_user(cls, user):
        """
        Get the staff record for a given user.
        Returns None if no staff record exists for the user.
        """
        try:
            return cls.objects.select_related('restaurant').get(user=user, is_deleted=False)
        except cls.DoesNotExist:
            return None

    @property
    def is_waiter(self):
        return any(g.name == Role.WAITER.value for g in self.user.groups.all())

    @property
    def is_manager(self):
        return any(g.name == Role.MANAGER.value for g in self.user.groups.all())

    @property
    def is_owner(self):
        return any(g.name == Role.OWNER.value for g in self.user.groups.all())

    @property
    def is_active(self):
        return not self.is_deleted
