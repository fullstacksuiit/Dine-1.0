from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils.decorators import method_decorator
from common.decorators import waiter_or_above_required
from sale.models.order import Order
from sale.serializers import OrderSerializer
from sale.services.billing_service import BillingService
from sale.services.ordering_service import OrderingService
from sale.services.helpers import handle_get_object_or_404, handle_serializer_validation


@method_decorator(waiter_or_above_required, name="dispatch")
class OrderAPI(APIView):
    """
    Class-based API for handling Orders (create, update, delete, retrieve).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Create new orders for a KOT (Kitchen Order Ticket).
        Expects: table, items, sizes, quantities, is_takeaway in request.data
        """
        try:
            kot, details = OrderingService.create_order_flow(
                request.restaurant, request.user, request.data
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

        # For API, just return KOT and details
        return Response(
            {"kot_id": kot.id, "details": details, "bill_id": kot.bill.id},
            status=status.HTTP_201_CREATED,
        )

    def put(self, request, order_id):
        """
        Update an existing order (quantity/size).
        Expects: order_id, quantity, size in request.data
        """
        order_obj = handle_get_object_or_404(Order, "id", order_id)
        if not order_obj:
            return Response(
                {"detail": "Order not found"}, status=status.HTTP_404_NOT_FOUND
            )
        order_serialiser = handle_serializer_validation(
            OrderSerializer, request.data, instance=order_obj
        )
        # Save the updated order instance with the new data
        order_serialiser.save(updated_by=request.user)
        return Response(order_serialiser.data, status=status.HTTP_202_ACCEPTED)

    def patch(self, request, order_id):
        """
        Partially update an existing order (specifically quantity).
        Expects: order_id, quantity in request.data
        """
        quantity = request.data.get("quantity")
        size = request.data.get("size")
        if size and not Order.Size.is_valid(size):
            return Response(
                {"detail": "Invalid size provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not quantity or not isinstance(quantity, int) or quantity <= 0:
            return Response(
                {"detail": "Valid quantity (positive integer) is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        order_obj = handle_get_object_or_404(Order, "id", order_id)
        if not order_obj:
            return Response(
                {"detail": "Order not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Update fields
        update_fields = ["quantity", "size", "updated_by"]
        order_obj.quantity = quantity
        order_obj.updated_by = request.user
        order_obj.size = size if size else order_obj.size
        if "notes" in request.data:
            order_obj.notes = (request.data["notes"] or "")[:200]
            update_fields.append("notes")
        order_obj.save(update_fields=update_fields)
        # Return the updated order data
        serializer = OrderSerializer(order_obj)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, order_id):
        """
        Hard delete an order (to match function-based view).
        Expects: order_id in request.data
        """
        order_obj = handle_get_object_or_404(Order, "id", order_id)
        if not order_obj:
            return Response(
                {"detail": "Order not found"}, status=status.HTTP_404_NOT_FOUND
            )
        order_obj.soft_delete()
        return Response({"detail": "Record Deleted"}, status=status.HTTP_200_OK)

    def get(self, request):
        """
        For API: Retrieve all active tables and dishes for order page (to match _generate_order_page).
        """
        active_tables = BillingService.get_active_bills(request.restaurant).values(
            "table_number", "id", "created_at"
        )
        return Response(
            {
                "active_tables": [
                    {
                        "id": table["id"],
                        "table_number": table["table_number"],
                        "created_at": table["created_at"].isoformat(),
                        "status": "active"
                    }
                    for table in active_tables
                ],
            },
            status=status.HTTP_200_OK,
        )
