from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils.decorators import method_decorator

from sale.models import KOT
from sale.serializers import KOTSerializer
from common.decorators import manager_or_above_required

@method_decorator(manager_or_above_required, name="get")
@method_decorator(manager_or_above_required, name="patch")
@method_decorator(manager_or_above_required, name="delete")
class KOTApi(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        if pk:
            # Get specific KOT
            kot = KOT.get_by_id(pk)
            if not kot:
                return Response({'detail': 'KOT not found'}, status=status.HTTP_404_NOT_FOUND)
            serializer = KOTSerializer(kot)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            # Get active KOTs for the restaurant (like kot_history view)
            try:
                restaurant = request.restaurant
                if not restaurant:
                    return Response({'detail': 'Restaurant not found'}, status=status.HTTP_400_BAD_REQUEST)

                # Get filter parameters
                order_filter = request.query_params.get('filter', 'dine-in')  # Default to dine-in

                # Get base queryset for active KOTs (create a general method equivalent)
                # Apply filtering based on order type
                if order_filter == 'takeaway':
                    # Filter for takeaway orders: is_takeaway=True OR order_type in ['TAKEAWAY', 'SWIGGY', 'ZOMATO']
                    kots = KOT.get_active_takeaway_KOTs(restaurant)
                else:
                    # Filter for dine-in orders: is_takeaway=False AND order_type='RESTAURANT'
                    kots = KOT.get_active_dine_in_KOTs(restaurant)

                # Separate pending and accepted KOTs exactly like kot_history view
                pending_kots = kots.filter(
                    accepted=False, status=KOT.Status.PENDING.value
                ).order_by("created_at")

                accepted_kots = (
                    kots.exclude(status=KOT.Status.CANCELLED.value)
                    .exclude(status=KOT.Status.PENDING.value)
                    .order_by("created_at")
                )

                # Serialize both sets (evaluate once, use len() to avoid extra count queries)
                pending_data = KOTSerializer(pending_kots, many=True).data
                accepted_data = KOTSerializer(accepted_kots, many=True).data

                # Return bifurcated data structure
                return Response({
                    'pending_kots': pending_data,
                    'accepted_kots': accepted_data,
                    'total_pending': len(pending_data),
                    'total_accepted': len(accepted_data),
                    'filter_applied': order_filter
                }, status=status.HTTP_200_OK)

            except Exception as e:
                return Response({'detail': f'Error fetching KOTs: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        pass

    def put(self, request, pk=None):
        pass

    def patch(self, request, pk):
        kot = KOT.get_by_id(pk)
        if not kot:
            return Response({'detail': 'KOT not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = KOTSerializer(kot, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            kot.refresh_from_db()
            # If the KOT is marked as COMPLETED, we should also complete the bill if it is a takeaway bill
            if kot.is_completed and kot.bill.is_takeaway:
                kot.bill.complete_bill(updated_by=request.user, active=False)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        kot = KOT.get_by_id(pk)
        if not kot:
            return Response({'detail': 'KOT not found'}, status=status.HTTP_404_NOT_FOUND)
        kot.cancel(request.staff)
        return Response(status=status.HTTP_204_NO_CONTENT)
