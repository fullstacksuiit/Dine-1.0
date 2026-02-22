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
from purchase.models.purchase_order_item import PurchaseOrderItem
from purchase.serializers import (
    PurchaseOrderSerializer,
    PurchaseOrderListSerializer,
)
from purchase.services.purchase_service import PurchaseService


@method_decorator(manager_or_above_required, name="dispatch")
class PurchaseOrderListCreateAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        status_filter = request.query_params.get("status")
        orders = PurchaseOrder.get_orders_for_restaurant(
            request.restaurant, status_filter=status_filter
        )

        search = request.query_params.get("search", "").strip()
        if search:
            orders = orders.filter(
                Q(order_number__icontains=search)
                | Q(vendor__name__icontains=search)
            )

        pagination, data = paginate_queryset(orders, request, PurchaseOrderListSerializer)
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

        order_number = request.data.get(
            "order_number",
            PurchaseService.generate_po_number(request.restaurant),
        )

        po = PurchaseOrder.objects.create(
            restaurant=request.restaurant,
            vendor=vendor,
            order_number=order_number,
            order_date=request.data.get("order_date"),
            expected_delivery_date=request.data.get("expected_delivery_date"),
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

            PurchaseOrderItem.objects.create(
                purchase_order=po,
                inventory_item=inv_item,
                item_name=inv_item.name,
                unit=inv_item.unit,
                quantity=quantity,
                unit_price=unit_price,
                tax_percent=tax_percent,
                amount=amount,
                updated_by=request.user,
            )

        PurchaseService.recalculate_order_totals(po)
        po.refresh_from_db()
        return Response(
            PurchaseOrderSerializer(po).data, status=status.HTTP_201_CREATED
        )


@method_decorator(manager_or_above_required, name="get")
@method_decorator(manager_or_above_required, name="put")
@method_decorator(owner_required, name="delete")
class PurchaseOrderDetailAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        po = PurchaseOrder.get_order_by_id(pk, request.restaurant)
        if not po:
            return Response(
                {"error": "Purchase order not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(PurchaseOrderSerializer(po).data)

    def put(self, request, pk):
        po = PurchaseOrder.get_order_by_id(pk, request.restaurant)
        if not po:
            return Response(
                {"error": "Purchase order not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if po.status != PurchaseOrder.Status.DRAFT.value:
            return Response(
                {"error": "Only DRAFT orders can be edited."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update PO fields
        for field in ["order_date", "expected_delivery_date", "notes"]:
            if field in request.data:
                setattr(po, field, request.data[field])

        if "vendor_id" in request.data:
            vendor = Vendor.get_vendor_by_id(
                request.data["vendor_id"], request.restaurant
            )
            if vendor:
                po.vendor = vendor

        po.updated_by = request.user
        po.save()

        # Replace items if provided
        items_data = request.data.get("items")
        if items_data is not None:
            po.items.filter(is_deleted=False).update(is_deleted=True)
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

                PurchaseOrderItem.objects.create(
                    purchase_order=po,
                    inventory_item=inv_item,
                    item_name=inv_item.name,
                    unit=inv_item.unit,
                    quantity=quantity,
                    unit_price=unit_price,
                    tax_percent=tax_percent,
                    amount=amount,
                    updated_by=request.user,
                )
            PurchaseService.recalculate_order_totals(po)

        po.refresh_from_db()
        return Response(PurchaseOrderSerializer(po).data)

    def delete(self, request, pk):
        po = PurchaseOrder.get_order_by_id(pk, request.restaurant)
        if not po:
            return Response(
                {"error": "Purchase order not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if po.status != PurchaseOrder.Status.DRAFT.value:
            return Response(
                {"error": "Only DRAFT orders can be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        po.soft_delete(request.user)
        return Response({"success": True})


@method_decorator(manager_or_above_required, name="dispatch")
class PurchaseOrderActionAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, action):
        po = PurchaseOrder.get_order_by_id(pk, request.restaurant)
        if not po:
            return Response(
                {"error": "Purchase order not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            if action == "approve":
                PurchaseService.approve_order(po, request.user)
            elif action == "receive":
                auto_invoice = request.data.get("auto_create_invoice", False)
                PurchaseService.receive_order(
                    po, request.user, auto_create_invoice=auto_invoice
                )
            elif action == "cancel":
                PurchaseService.cancel_order(po, request.user)
            else:
                return Response(
                    {"error": "Invalid action. Use: approve, receive, cancel"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

        po.refresh_from_db()
        return Response(PurchaseOrderSerializer(po).data)
