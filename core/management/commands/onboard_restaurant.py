from django.core.management.base import BaseCommand
from core.scripts.onboard_restaurant import onboard_restaurant

class Command(BaseCommand):
    help = 'Onboard a new restaurant by name and print its ID.'

    def add_arguments(self, parser):
        parser.add_argument('name', type=str, help='Name of the restaurant to onboard')

    def handle(self, *args, **options):
        name = options['name']
        restaurant = onboard_restaurant(name)
        self.stdout.write(self.style.SUCCESS(f'Restaurant onboarded with ID: {restaurant.id}'))
