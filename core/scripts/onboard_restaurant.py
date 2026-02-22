from core.models import Restaurant, Subscription
from sale.models.course import Course
from purchase.models.expense_category import ExpenseCategory


def _create_courses(restaurant):
    """Helper function to create default courses for a restaurant."""
    courses = [
        "Starters",
        "Main Course",
        "Dessert",
        "Beverages",
        "Salads",
        "Soups",
        "Chinese",
        "Indian",
        "Continental",
    ]

    # Recreate the courses to add in the ordering of the Menu
    Course.objects.filter(
        name__in=courses, restaurant=restaurant
    ).delete()  # Clear existing courses
    for course_name in courses:
        Course.objects.create(name=course_name, restaurant=restaurant)
        print(f"Course '{course_name}' created for restaurant '{restaurant.name}'")


def _add_subscription(restaurant):
    """Helper function to add a subscription for the restaurant."""
    Subscription.objects.get_or_create(
        restaurant=restaurant,
        plan_name=Subscription.Plan.STARTER.value,
    )
    print(f"Subscription added for restaurant '{restaurant.name}'")


def onboard_restaurant(name):
    restaurant, created = Restaurant.objects.get_or_create(name=name)
    if created:
        print(f"Restaurant '{name}' created with ID: {restaurant.id}")
        restaurant.display_name = name
        restaurant.save()

    else:
        print(f"Restaurant '{name}' already exists with ID: {restaurant.id}")

    _add_subscription(restaurant)
    _create_courses(restaurant)
    _create_expense_categories(restaurant)
    return restaurant


def _create_expense_categories(restaurant):
    """Helper function to create default expense categories for a restaurant."""
    categories = [
        "Ingredients",
        "Utilities",
        "Rent",
        "Salaries",
        "Maintenance",
        "Marketing",
        "Miscellaneous",
    ]
    for name in categories:
        _, created = ExpenseCategory.objects.get_or_create(
            restaurant=restaurant, name=name, defaults={"is_deleted": False}
        )
        if created:
            print(f"Expense category '{name}' created for restaurant '{restaurant.name}'")
