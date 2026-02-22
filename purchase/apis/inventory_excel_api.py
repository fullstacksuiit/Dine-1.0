from django.http import HttpResponse
from django.utils.decorators import method_decorator
from rest_framework import permissions, status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from common.decorators import manager_or_above_required, owner_required
from purchase.services.inventory_excel_service import InventoryExcelService


@method_decorator(manager_or_above_required, name="dispatch")
class InventoryExportAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        excel_bytes = InventoryExcelService.export_to_excel(request.restaurant)
        response = HttpResponse(
            excel_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="inventory.xlsx"'
        return response


@method_decorator(owner_required, name="dispatch")
class InventoryImportAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        file = request.FILES.get("file")
        if not file:
            return Response(
                {"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not file.name.endswith((".xlsx", ".xls")):
            return Response(
                {"error": "Only .xlsx or .xls files are supported"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = InventoryExcelService.import_from_excel(
            file.read(), request.restaurant, request.user
        )
        return Response(result, status=status.HTTP_200_OK)
