from django.db import models
from core.models.base import BaseModel
from core.models.restaurant import Restaurant


class Course(BaseModel):
    name = models.CharField(max_length=100)
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="courses",
        help_text="Restaurant this course belongs to",
    )

    class Meta(BaseModel.Meta):
        unique_together = ["restaurant", "name"]
        verbose_name = "Course"
        verbose_name_plural = "Courses"
        indexes = [
            models.Index(fields=["restaurant", "is_deleted"]),
        ]


    @classmethod
    def get_courses_for_restaurant(cls, restaurant):
        """
        Get all courses for a specific restaurant.
        Returns an empty queryset if no courses exist.
        """
        return cls.objects.filter(restaurant=restaurant, is_deleted=False).order_by(
            "name"
        )

    @classmethod
    def get_or_create_course_by_name(cls, name, restaurant):
        """
        Get a course by its name within a specific restaurant.
        Returns None if the course does not exist or is deleted.
        """
        course, _ = cls.objects.get_or_create(name=name, restaurant=restaurant)
        if course.is_deleted:
            course.un_delete()
        return course

    def __str__(self):
        return (
            f"{self.restaurant.display_name} - {self.name}"
            if hasattr(self.restaurant, "display_name")
            else self.name
        )
