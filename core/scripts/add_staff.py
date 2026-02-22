import random
import string
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from core.models.restaurant import Restaurant
from core.models.staff import Staff

def add_staff(restaurant_id, username, role, password=None):
    User = get_user_model()
    # Generate a random password
    if not password:
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    # Create user
    user, created = User.objects.get_or_create(username=username)
    if created:
        user.set_password(password)
        user.save()
    else:
        # If user exists, check if staff exists for another restaurant
        if Staff.objects.filter(user=user, is_deleted=False).exclude(restaurant_id=restaurant_id).exists():
            print(f"User {username} already exists as staff for another restaurant.")
            return None, None, None
        # If user exists for this restaurant, update password
        user.set_password(password)
        user.save()
    # Get restaurant
    restaurant = Restaurant.objects.get(id=restaurant_id)
    # Create staff entry (do not set role field)
    staff, _ = Staff.objects.get_or_create(user=user, restaurant=restaurant)
    staff.is_deleted = False
    staff.save()
    # Assign user to the correct group for RBAC
    if role:
        group, _ = Group.objects.get_or_create(name=role.upper())
        user.groups.clear()
        user.groups.add(group)
    return user, staff, password

