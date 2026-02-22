from django.core.management.base import BaseCommand
from core.models.restaurant import Restaurant
from purchase.models.expense_category import ExpenseCategory


DEFAULT_CATEGORIES = [
    "Ingredients",
    "Utilities",
    "Rent",
    "Salaries",
    "Maintenance",
    "Marketing",
    "Miscellaneous",
]


class Command(BaseCommand):
    help = "Seed default expense categories for a restaurant."

    def add_arguments(self, parser):
        parser.add_argument(
            "restaurant_id",
            type=str,
            help="UUID of the restaurant to seed categories for",
        )

    def handle(self, *args, **options):
        restaurant_id = options["restaurant_id"]
        try:
            restaurant = Restaurant.objects.get(id=restaurant_id)
        except Restaurant.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Restaurant not found: {restaurant_id}"))
            return

        created_count = 0
        for name in DEFAULT_CATEGORIES:
            category, created = ExpenseCategory.objects.get_or_create(
                restaurant=restaurant,
                name=name,
                defaults={"is_deleted": False},
            )
            if created:
                created_count += 1
                self.stdout.write(f"  Created: {name}")
            elif category.is_deleted:
                category.un_delete()
                created_count += 1
                self.stdout.write(f"  Restored: {name}")
            else:
                self.stdout.write(f"  Exists:   {name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {created_count} categories created/restored for '{restaurant.name}'."
            )
        )
