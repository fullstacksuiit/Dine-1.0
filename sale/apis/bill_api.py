import re

from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view

from sale.models import Bill
from sale.serializers import BillSerializer, OrderSerializer
from sale.services import BillingService
from common.decorators import manager_or_above_required, subscription_required, waiter_or_above_required


@method_decorator(subscription_required, name="dispatch")
@method_decorator(waiter_or_above_required, name="get")
@method_decorator(manager_or_above_required, name="patch")
@method_decorator(manager_or_above_required, name="delete")
class BillApi(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        bill = get_object_or_404(Bill, pk=pk)
        group = request.query_params.get("group", "false")  # @Rule Clean Module Interfaces - Default to ungrouped for easier editing
        bill_data = BillSerializer(bill).data

        if group == "false":
            orders = bill.get_orders()
            return Response(
                {
                    "bill_details": bill_data,
                    "orders": OrderSerializer(orders, many=True).data,
                },
                status=status.HTTP_200_OK,
            )

        # Grouped response when explicitly requested
        grouped_orders = BillingService.group_orders_by_dish_and_size(bill)
        return Response(
            {"bill_details": bill_data, "orders": grouped_orders},
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        ...

    def put(self, request, pk=None):
        bill = get_object_or_404(Bill, pk=pk)
        was_already_completed = not bill.active
        bill = BillingService.update_bill_from_request(bill, request.data, request.user)
        if was_already_completed:
            bill.is_edited = True
            bill.save(update_fields=["is_edited"])
        return Response(BillSerializer(bill).data, status=status.HTTP_202_ACCEPTED)

    def patch(self, request, pk=None):
        bill = get_object_or_404(Bill, pk=pk)
        was_already_completed = not bill.active
        extra = {"updated_by": request.user}
        if was_already_completed:
            extra["is_edited"] = True
        serializer = BillSerializer(bill, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(**extra)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk=None):
        bill = get_object_or_404(Bill, pk=pk)
        bill.soft_delete(request.user)
        return Response({"detail": "Record Deleted"}, status=status.HTTP_200_OK)


@method_decorator(subscription_required, name="dispatch")
@method_decorator(waiter_or_above_required, name="post")
class BillSettleApi(APIView):
    """Mark a completed bill as paid with the given payment type."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        bill = get_object_or_404(Bill, pk=pk, is_deleted=False)

        if bill.restaurant_id != request.restaurant.id:
            return Response(
                {"detail": "Bill does not belong to your restaurant."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if bill.active:
            return Response(
                {"detail": "Cannot settle an active bill. Complete the bill first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment_type = request.data.get("payment_type")
        if not payment_type or payment_type not in ("CASH", "UPI", "CARD", "CREDIT"):
            return Response(
                {"detail": "payment_type is required. Must be CASH, UPI, CARD, or CREDIT."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if payment_type == "CREDIT":
            # Credit: record the payment type but keep the bill UNPAID
            # so it counts toward customer outstanding balance.
            bill.payment_type = payment_type
            bill.updated_by = request.user
            bill.save(update_fields=["payment_type", "updated_by"])
        else:
            bill.settle_bill(payment_type=payment_type, updated_by=request.user)
        return Response(BillSerializer(bill).data, status=status.HTTP_200_OK)


@method_decorator(waiter_or_above_required, name="post")
class BillMergeApi(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        """Merge a source table's orders into the target table (pk)."""
        source_bill_id = request.data.get("source_bill_id")
        if not source_bill_id:
            return Response(
                {"detail": "source_bill_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target_bill = get_object_or_404(Bill, pk=pk, is_deleted=False)
        source_bill = get_object_or_404(Bill, pk=source_bill_id, is_deleted=False)

        # Ensure both belong to the request user's restaurant
        restaurant = request.restaurant
        if target_bill.restaurant_id != restaurant.id or source_bill.restaurant_id != restaurant.id:
            return Response(
                {"detail": "Bills must belong to your restaurant."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            orders_transferred = BillingService.merge_tables(
                source_bill, target_bill, request.user
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "merged": True,
                "orders_transferred": orders_transferred,
                "source_table": source_bill.table_number,
                "target_table": target_bill.table_number,
            },
            status=status.HTTP_200_OK,
        )


@api_view(["GET"])
def bill_kot_status_api(request, restaurant_id):
    """
    API endpoint to check if a bill with the given invoice number exists (supports full invoice number in format YY-YY/invoice_number),
    get the latest bill, then get the latest KOT related to it and return its status.
    """
    invoice_number = request.GET.get("invoice_number")
    if not invoice_number:
        return Response({"detail": "Missing invoice_number parameter."}, status=status.HTTP_400_BAD_REQUEST)
    # Check if it's a full invoice number (format: YY-YY/invoice_number)
    full_invoice_match = re.match(r"^(\d{2}-\d{2})/(\d+)$", invoice_number)
    if full_invoice_match:
        # It's a full invoice number, search by full_invoice_number property
        fiscal_prefix, inv_num = full_invoice_match.groups()
        # Find all bills for this restaurant with this invoice_number
        bills = Bill.objects.filter(restaurant_id=restaurant_id, invoice_number=inv_num, is_deleted=False)
        # Filter by fiscal year prefix
        bill = None
        for b in bills.order_by("-created_at"):
            if b.full_invoice_number == invoice_number:
                bill = b
                break
    else:
        # Not a full invoice number, just search by invoice_number and get latest
        bill = Bill.objects.filter(restaurant_id=restaurant_id, invoice_number=invoice_number, is_deleted=False).latest("created_at")

    if not bill:
        return Response({"exists": False, "detail": "Bill not found"}, status=status.HTTP_404_NOT_FOUND)
    # Get the latest KOT related to this bill
    kot = bill.kots.filter(is_deleted=False).latest("created_at") if bill.kots.exists() else None
    kot_status = kot.status if kot else None
    return Response(
        {
            "exists": True,
            "bill_id": bill.id,
            "invoice_number": bill.invoice_number,
            "full_invoice_number": bill.full_invoice_number,
            "kot_id": kot.id if kot else None,
            "kot_status": kot_status,
        },
        status=status.HTTP_200_OK,
    )
