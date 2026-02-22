from decimal import Decimal
from django.db.models import Q
from django.utils.decorators import method_decorator
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.decorators import manager_or_above_required, owner_required
from common.pagination import paginate_queryset
from purchase.models.vendor import Vendor
from purchase.models.customer import Customer
from purchase.models.payment import Payment
from purchase.models.purchase_invoice import PurchaseInvoice
from purchase.serializers import PaymentSerializer
from purchase.services.payment_service import PaymentService


@method_decorator(manager_or_above_required, name="dispatch")
class PaymentListCreateAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = Payment.objects.filter(
            restaurant=request.restaurant, is_deleted=False
        ).select_related("vendor", "customer").order_by("-payment_date")

        payment_type = request.query_params.get("payment_type")
        if payment_type:
            qs = qs.filter(payment_type=payment_type)

        vendor_id = request.query_params.get("vendor_id")
        if vendor_id:
            qs = qs.filter(vendor_id=vendor_id)

        customer_id = request.query_params.get("customer_id")
        if customer_id:
            qs = qs.filter(customer_id=customer_id)

        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(vendor__name__icontains=search)
                | Q(customer__name__icontains=search)
                | Q(reference_number__icontains=search)
            )

        pagination, data = paginate_queryset(qs, request, PaymentSerializer)
        if pagination:
            return Response({"results": data, "pagination": pagination})
        return Response(data)

    def post(self, request):
        payment_type = request.data.get("payment_type")
        if payment_type not in Payment.PaymentType.values():
            return Response(
                {"error": f"Invalid payment_type. Use one of: {Payment.PaymentType.values()}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        amount = Decimal(str(request.data.get("amount", 0)))
        if amount <= 0:
            return Response(
                {"error": "Amount must be greater than 0"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment_mode = request.data.get("payment_mode", Payment.PaymentMode.CASH.value)
        payment_date = request.data.get("payment_date")
        reference_number = request.data.get("reference_number")
        notes = request.data.get("notes")

        if payment_type == Payment.PaymentType.VENDOR_PAYMENT.value:
            vendor = Vendor.get_vendor_by_id(
                request.data.get("vendor_id"), request.restaurant
            )
            if not vendor:
                return Response(
                    {"error": "Vendor not found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            purchase_invoice = None
            invoice_id = request.data.get("purchase_invoice_id")
            if invoice_id:
                purchase_invoice = PurchaseInvoice.get_invoice_by_id(
                    invoice_id, request.restaurant
                )

            payment = PaymentService.record_vendor_payment(
                restaurant=request.restaurant,
                vendor=vendor,
                amount=amount,
                payment_mode=payment_mode,
                payment_date=payment_date,
                purchase_invoice=purchase_invoice,
                reference_number=reference_number,
                notes=notes,
                user=request.user,
            )

        elif payment_type == Payment.PaymentType.CUSTOMER_RECEIPT.value:
            customer = Customer.get_customer_by_id(
                request.data.get("customer_id"), request.restaurant
            )
            if not customer:
                return Response(
                    {"error": "Customer not found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            payment = PaymentService.record_customer_payment(
                restaurant=request.restaurant,
                customer=customer,
                amount=amount,
                payment_mode=payment_mode,
                payment_date=payment_date,
                reference_number=reference_number,
                notes=notes,
                user=request.user,
            )
        else:
            return Response(
                {"error": "Invalid payment type"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


@method_decorator(manager_or_above_required, name="get")
@method_decorator(owner_required, name="delete")
class PaymentDetailAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            payment = Payment.objects.select_related(
                "vendor", "customer", "purchase_invoice"
            ).get(id=pk, restaurant=request.restaurant, is_deleted=False)
        except Payment.DoesNotExist:
            return Response(
                {"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(PaymentSerializer(payment).data)

    def delete(self, request, pk):
        try:
            payment = Payment.objects.select_related("purchase_invoice").get(
                id=pk, restaurant=request.restaurant, is_deleted=False
            )
        except Payment.DoesNotExist:
            return Response(
                {"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Reverse invoice amount_paid if linked
        if payment.purchase_invoice:
            invoice = payment.purchase_invoice
            invoice.amount_paid -= payment.amount
            if invoice.amount_paid <= 0:
                invoice.amount_paid = Decimal("0.00")
                invoice.status = PurchaseInvoice.Status.PENDING.value
            elif invoice.amount_paid < invoice.total_amount:
                invoice.status = PurchaseInvoice.Status.PARTIALLY_PAID.value
            invoice.save(update_fields=["amount_paid", "status", "updated_at"])

        payment.soft_delete(request.user)
        return Response({"success": True})
