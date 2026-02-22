from functools import wraps
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from core.models.staff import Staff

ROLE_HIERARCHY = {
    'waiter': 1,
    'manager': 2,
    'owner': 3,
}

def get_staff_role_level(staff):
    if hasattr(staff, 'is_owner') and staff.is_owner:
        return ROLE_HIERARCHY['owner']
    if hasattr(staff, 'is_manager') and staff.is_manager:
        return ROLE_HIERARCHY['manager']
    if hasattr(staff, 'is_waiter') and staff.is_waiter:
        return ROLE_HIERARCHY['waiter']
    return 0

def role_required(min_role):
    """
    Decorator factory: allows access to users with at least the given role (waiter, manager, owner).
    """
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            staff = getattr(request, 'staff', None)
            if not staff or not isinstance(staff, Staff) or not staff.restaurant:
                return HttpResponse("You must be a staff member of a restaurant to access this page.", status=403)
            required_level = ROLE_HIERARCHY[min_role]
            user_level = get_staff_role_level(staff)
            if user_level < required_level:
                return HttpResponse(f"You must be a {min_role} or above to access this page.", status=403)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def subscription_required(view_func):
    """
    Decorator to ensure the restaurant has an active subscription.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        restaurant = getattr(request, 'restaurant', None)
        if not restaurant:
            return HttpResponse("Forbidden", status=403)
        if not restaurant.has_active_subscription:
            return HttpResponse("This restaurant does not have an active subscription.", status=403)
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# Usage aliases for clarity
waiter_or_above_required = role_required('waiter')
manager_or_above_required = role_required('manager')
owner_required = role_required('owner')