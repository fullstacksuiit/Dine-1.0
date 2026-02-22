from decimal import Decimal
from django.db.models import Q
from django.utils.decorators import method_decorator
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.decorators import manager_or_above_required, owner_required
from common.pagination import paginate_queryset
from purchase.models.vendor import Vendor
from purchase.models.inventory_item import InventoryItem
from purchase.models.purchase_order import PurchaseOrder
from purchase.models.purchase_invoice import PurchaseInvoice
from purchase.models.purchase_invoice_item import PurchaseInvoiceItem
from purchase.serializers import (
    PurchaseInvoiceSerializer,
    PurchaseInvoiceListSerializer,
)
from purchase.services.purchase_service import PurchaseService
from purchase.services.stock_service import StockService


@method_decorator(manager_or_above_required, name="dispatch")
class PurchaseInvoiceListCreateAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        status_filter = request.query_params.get("status")
        vendor_id = request.query_params.get("vendor_id")

        invoices = PurchaseInvoice.get_invoices_for_restaurant(
            request.restaurant, status_filter=status_filter
        )
        if vendor_id:
            invoices = invoices.filter(vendor_id=vendor_id)

        search = request.query_params.get("search", "").strip()
        if search:
            invoices = invoices.filter(
                Q(invoice_number__icontains=search)
                | Q(vendor__name__icontains=search)
            )

        pagination, data = paginate_queryset(invoices, request, PurchaseInvoiceListSerializer)
        if pagination:
            return Response({"results": data, "pagination": pagination})
        return Response(data)

    def post(self, request):
        vendor_id = request.data.get("vendor_id")
        vendor = Vendor.get_vendor_by_id(vendor_id, request.restaurant)
        if not vendor:
            return Response(
                {"error": "Vendor not found"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Optional PO link
        purchase_order = None
        po_id = request.data.get("purchase_order_id")
        if po_id:
            purchase_order = PurchaseOrder.get_order_by_id(po_id, request.restaurant)

        invoice = PurchaseInvoice.objects.create(
            restaurant=request.restaurant,
            vendor=vendor,
            purchase_order=purchase_order,
            invoice_number=request.data.get("invoice_number", ""),
            invoice_date=request.data.get("invoice_date"),
            due_date=request.data.get("due_date"),
            cgst=Decimal(str(request.data.get("cgst", 0))),
            sgst=Decimal(str(request.data.get("sgst", 0))),
            igst=Decimal(str(request.data.get("igst", 0))),
            discount=Decimal(str(request.data.get("discount", 0))),
            notes=request.data.get("notes", ""),
            updated_by=request.user,
        )

        # Create line items
        items_data = request.data.get("items", [])
        for item_data in items_data:
            inv_item = InventoryItem.get_item_by_id(
                item_data.get("inventory_item_id"), request.restaurant
            )
            if not inv_item:
                continue

            quantity = Decimal(str(item_data.get("quantity", 0)))
            unit_price = Decimal(str(item_data.get("unit_price", 0)))
            tax_percent = Decimal(str(item_data.get("tax_percent", 0)))
            tax_amount = quantity * unit_price * tax_percent / 100
            amount = quantity * unit_price + tax_amount

            PurchaseInvoiceItem.objects.create(
                purchase_invoice=invoice,
                inventory_item=inv_item,
                item_name=inv_item.name,
                unit=inv_item.unit,
                quantity=quantity,
                unit_price=unit_price,
                tax_percent=tax_percent,
                amount=amount,
                updated_by=request.user,
            )

        PurchaseService.recalculate_invoice_totals(invoice)

        # Auto-create stock entries from invoice items
        StockService.add_stock_from_invoice(invoice, user=request.user)

        invoice.refresh_from_db()
        return Response(
            PurchaseInvoiceSerializer(invoice).data,
            status=status.HTTP_201_CREATED,
        )


@method_decorator(manager_or_above_required, name="get")
@method_decorator(manager_or_above_required, name="put")
@method_decorator(owner_required, name="delete")
class PurchaseInvoiceDetailAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        invoice = PurchaseInvoice.get_invoice_by_id(pk, request.restaurant)
        if not invoice:
            return Response(
                {"error": "Invoice not found"}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(PurchaseInvoiceSerializer(invoice).data)

    def put(self, request, pk):
        invoice = PurchaseInvoice.get_invoice_by_id(pk, request.restaurant)
        if not invoice:
            return Response(
                {"error": "Invoice not found"}, status=status.HTTP_404_NOT_FOUND
            )
        if invoice.status != PurchaseInvoice.Status.PENDING.value:
            return Response(
                {"error": "Only PENDING invoices can be edited."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for field in ["invoice_number", "invoice_date", "due_date", "notes"]:
            if field in request.data:
                setattr(invoice, field, request.data[field])

        for field in ["cgst", "sgst", "igst", "discount"]:
            if field in request.data:
                setattr(invoice, field, Decimal(str(request.data[field])))

        invoice.updated_by = request.user
        invoice.save()

        invoice.refresh_from_db()
        return Response(PurchaseInvoiceSerializer(invoice).data)

    def delete(self, request, pk):
        invoice = PurchaseInvoice.get_invoice_by_id(pk, request.restaurant)
        if not invoice:
            return Response(
                {"error": "Invoice not found"}, status=status.HTTP_404_NOT_FOUND
            )
        invoice.soft_delete(request.user)
        return Response({"success": True})
