from django.db import models
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsOwner, IsOwnerOrManager
from core.models.table import Table


class TableListCreateAPI(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrManager]

    def get(self, request):
        tables = Table.get_tables_for_restaurant(request.restaurant)
        data = [
            {
                "id": str(t.id),
                "name": t.name,
                "display_order": t.display_order,
            }
            for t in tables
        ]
        return Response(data)

    def post(self, request):
        name = request.data.get("name", "").strip()
        if not name:
            return Response(
                {"error": "Table name is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(name) > 50:
            return Response(
                {"error": "Table name must be 50 characters or less."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if Table.objects.filter(
            restaurant=request.restaurant, name=name, is_deleted=False
        ).exists():
            return Response(
                {"error": f"A table named '{name}' already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        max_order = (
            Table.objects.filter(
                restaurant=request.restaurant, is_deleted=False
            ).aggregate(models.Max("display_order"))["display_order__max"]
            or 0
        )

        # Revive soft-deleted table with the same name if one exists,
        # otherwise create a new one.
        table, created = Table.objects.get_or_create(
            restaurant=request.restaurant,
            name=name,
            defaults={
                "display_order": request.data.get("display_order", max_order + 1),
                "updated_by": request.user,
            },
        )
        if not created:
            table.is_deleted = False
            table.display_order = request.data.get("display_order", max_order + 1)
            table.updated_by = request.user
            table.save()
        return Response(
            {
                "id": str(table.id),
                "name": table.name,
                "display_order": table.display_order,
            },
            status=status.HTTP_201_CREATED,
        )


class TableDetailAPI(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrManager]

    def put(self, request, pk):
        table = get_object_or_404(
            Table, id=pk, restaurant=request.restaurant, is_deleted=False
        )
        name = request.data.get("name", "").strip()
        if name and name != table.name:
            if (
                Table.objects.filter(
                    restaurant=request.restaurant, name=name, is_deleted=False
                )
                .exclude(id=pk)
                .exists()
            ):
                return Response(
                    {"error": f"A table named '{name}' already exists."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            table.name = name
        if "display_order" in request.data:
            try:
                table.display_order = int(request.data["display_order"])
            except (ValueError, TypeError):
                pass
        table.updated_by = request.user
        table.save()
        return Response({"success": True})

    def delete(self, request, pk):
        table = get_object_or_404(
            Table, id=pk, restaurant=request.restaurant, is_deleted=False
        )
        table.soft_delete(request.user)
        return Response({"success": True})
