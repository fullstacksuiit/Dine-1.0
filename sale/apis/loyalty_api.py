from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils.decorators import method_decorator

from common.decorators import waiter_or_above_required
from sale.services.loyalty_service import LoyaltyService


@method_decorator(waiter_or_above_required, name="dispatch")
class CustomerLoyaltyAPIView(APIView):
    """
    API to get customer loyalty information based on contact number.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get loyalty information for a customer.
        Query parameters:
        - contact: Customer's contact number
        """
        contact = request.GET.get('contact', '').strip()

        if not contact:
            return Response(
                {'error': 'Contact number is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get loyalty information
        loyalty_info = LoyaltyService.get_customer_loyalty_info(
            contact=contact,
            restaurant=request.restaurant
        )

        return Response(loyalty_info, status=status.HTTP_200_OK)


@method_decorator(waiter_or_above_required, name="dispatch")
class RestaurantLoyaltySummaryAPIView(APIView):
    """
    API to get restaurant-wide loyalty summary.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get loyalty summary for the restaurant.
        Query parameters:
        - days: Number of days to look back (default: 30)
        """
        days = int(request.GET.get('days', 30))

        summary = LoyaltyService.get_restaurant_loyalty_summary(
            restaurant=request.restaurant,
            days=days
        )

        return Response(summary, status=status.HTTP_200_OK)
