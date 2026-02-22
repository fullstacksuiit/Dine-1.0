from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser

from core.models.staff import Staff


class StaffMiddleware(MiddlewareMixin):
    """
    Middleware that injects the Staff record into the request object
    for authenticated users who are restaurant staff members.

    Adds:
    - request.staff - The Staff record for the authenticated user (or None)
    - request.restaurant - The Restaurant associated with the staff member (or None)
    """

    def process_request(self, request):
        """Process each request to attach staff and restaurant data if available."""
        # Initialize with None values
        request.staff = None
        request.restaurant = None

        # Only process for authenticated users
        if not request.user or isinstance(request.user, AnonymousUser):
            return None

        # Try to find the staff record for this user
        staff = Staff.get_staff_by_user(request.user)

        if staff:
            # Attach staff and restaurant objects to the request
            request.staff = staff
            request.restaurant = staff.restaurant

        return None