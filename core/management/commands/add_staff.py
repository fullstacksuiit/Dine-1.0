from django.core.management.base import BaseCommand
from core.scripts.add_staff import add_staff

class Command(BaseCommand):
    help = 'Add a staff member to a restaurant. Prints username and password.'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username for the staff user')
        parser.add_argument('role', type=str, help='Role for the staff (waiter, manager, owner)')
        parser.add_argument('--password', type=str, default=None, help='Optional password for the staff user')
        parser.add_argument('restaurant_id', type=str, help='ID of the restaurant')

    def handle(self, *args, **options):
        restaurant_id = options['restaurant_id']
        username = options['username']
        role = options['role']
        password = options.get('password')
        if password:
            user, staff, password = add_staff(restaurant_id, username, role, password=password)
        else:
            user, staff, password = add_staff(restaurant_id, username, role)
        if user and staff:
            self.stdout.write(self.style.SUCCESS(f'Username: {username}\nPassword: {password}\nRestaurant: {staff.restaurant.name}\nRole: {role}'))
        else:
            self.stdout.write(self.style.ERROR('Staff creation failed or user already exists for another restaurant.'))
