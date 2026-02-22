from core.models.base import BaseModel
from core.models.restaurant import Restaurant
from django.db import models


class Menu(BaseModel):
    restaurant = models.ForeignKey(
        Restaurant, on_delete=models.CASCADE, related_name="menus", db_index=True, unique=True,
    )
    ordering = models.JSONField(
        default=list,
        help_text="List of course IDs in the order they should appear in the menu.",
    )

    @classmethod
    def get_menu_by_restaurant(cls, restaurant: Restaurant):
        """
        Retrieve the menu for a specific restaurant.
        If no menu exists, create a new one.
        """
        try:
            return cls.objects.get(restaurant=restaurant, is_deleted=False)
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_or_create_menu_by_restaurant(cls, restaurant: Restaurant):
        """
        Get or create a menu for a specific restaurant.
        If no menu exists, create a new one with an empty ordering.
        """
        menu, created = cls.objects.get_or_create(restaurant=restaurant, is_deleted=False)
        if created:
            menu.ordering = []
            menu.save()
        return menu
