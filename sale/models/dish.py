from django.db import models
from core.models.restaurant import Restaurant
from core.models.base import BaseModel
from .course import Course


class Dish(BaseModel):
    """Model definition for Dish."""

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="dishes",
        help_text="Restaurant this dish belongs to",
    )
    name = models.CharField(max_length=150)
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dishes',
        help_text="Course this dish belongs to (optional, new field)",
    )

    restaurant_half_price = models.FloatField()
    restaurant_full_price = models.FloatField()

    zomato_half_price = models.FloatField()
    zomato_full_price = models.FloatField()

    swiggy_full_price = models.FloatField()
    swiggy_half_price = models.FloatField()

    class Meta(BaseModel.Meta):
        """Meta definition for Dish."""

        verbose_name = "Dish"
        verbose_name_plural = "Dishes"
        indexes = [
            models.Index(fields=["restaurant", "is_deleted"]),
        ]


    @classmethod
    def get_dishes_for_restaurant(cls, restaurant):
        """
        Get all dishes for a specific restaurant.
        Returns an empty queryset if no dishes exist.
        """
        return cls.objects.select_related("course").filter(restaurant=restaurant, is_deleted=False)

    @classmethod
    def get_dish_by_id(cls, dish_id: str, restaurant: Restaurant):
        """
        Retrieve a dish by its ID.
        Returns None if no dish is found.
        """
        try:
            return cls.objects.get(id=dish_id, restaurant=restaurant, is_deleted=False)
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_dish_for_restaurant(cls, restaurant: Restaurant, dish_id: str):
        return cls.objects.filter(id=dish_id, restaurant=restaurant, is_deleted=False)

    def __str__(self):
        """Unicode representation of Dish."""
        return (
            f"{self.restaurant.display_name} - {self.name} : {self.course.name} "
            if self.name and self.course
            else f"{self.restaurant.display_name} - {self.name} : Unnamed Course"
        )
