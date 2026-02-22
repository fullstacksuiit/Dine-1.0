from django.db.models import Q
from django.utils.decorators import method_decorator
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.decorators import (
    waiter_or_above_required,
    manager_or_above_required,
    owner_required,
)
from common.pagination import paginate_queryset
from purchase.models.inventory_item import InventoryItem
from purchase.models.stock_entry import StockEntry
from purchase.serializers import InventoryItemSerializer, StockEntrySerializer
from purchase.services.stock_service import StockService


@method_decorator(waiter_or_above_required, name="get")
@method_decorator(manager_or_above_required, name="post")
class InventoryListCreateAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        items = InventoryItem.get_items_for_restaurant(request.restaurant)

        search = request.query_params.get("search", "").strip()
        if search:
            items = items.filter(
                Q(name__icontains=search)
                | Q(category__name__icontains=search)
            )

        pagination, data = paginate_queryset(items, request, InventoryItemSerializer)
        if pagination:
            return Response({"results": data, "pagination": pagination})
        return Response(data)

    def post(self, request):
        serializer = InventoryItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        name = serializer.validated_data.get("name", "").strip()
        if InventoryItem.objects.filter(
            restaurant=request.restaurant, name=name, is_deleted=False
        ).exists():
            return Response(
                {"error": f"An inventory item named '{name}' already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save(restaurant=request.restaurant, updated_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@method_decorator(manager_or_above_required, name="dispatch")
class LowStockAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        items = InventoryItem.get_low_stock_items(request.restaurant)
        return Response(InventoryItemSerializer(items, many=True).data)


@method_decorator(waiter_or_above_required, name="get")
@method_decorator(manager_or_above_required, name="put")
@method_decorator(owner_required, name="delete")
class InventoryDetailAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        item = InventoryItem.get_item_by_id(pk, request.restaurant)
        if not item:
            return Response(
                {"error": "Inventory item not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        history = StockService.get_stock_history(item, request.restaurant)
        return Response(
            {
                "item": InventoryItemSerializer(item).data,
                "stock_history": StockEntrySerializer(history, many=True).data,
            }
        )

    def put(self, request, pk):
        item = InventoryItem.get_item_by_id(pk, request.restaurant)
        if not item:
            return Response(
                {"error": "Inventory item not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = InventoryItemSerializer(item, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)

    def delete(self, request, pk):
        item = InventoryItem.get_item_by_id(pk, request.restaurant)
        if not item:
            return Response(
                {"error": "Inventory item not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        item.soft_delete(request.user)
        return Response({"success": True})


@method_decorator(manager_or_above_required, name="dispatch")
class StockEntryCreateAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        item = InventoryItem.get_item_by_id(pk, request.restaurant)
        if not item:
            return Response(
                {"error": "Inventory item not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        entry_type = request.data.get("entry_type")
        if entry_type not in StockEntry.EntryType.values():
            return Response(
                {"error": f"Invalid entry_type. Use one of: {StockEntry.EntryType.values()}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        quantity = request.data.get("quantity")
        if not quantity:
            return Response(
                {"error": "quantity is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        entry = StockService.manual_stock_adjustment(
            inventory_item=item,
            quantity=quantity,
            entry_type=entry_type,
            restaurant=request.restaurant,
            user=request.user,
            notes=request.data.get("notes"),
        )
        return Response(StockEntrySerializer(entry).data, status=status.HTTP_201_CREATED)
