from django.db.models import Q
from django.utils.decorators import method_decorator
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.decorators import manager_or_above_required, owner_required
from common.pagination import paginate_queryset
from purchase.models.vendor import Vendor
from purchase.serializers import VendorSerializer


@method_decorator(manager_or_above_required, name="dispatch")
class VendorListCreateAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        vendors = Vendor.get_vendors_for_restaurant(request.restaurant)

        search = request.query_params.get("search", "").strip()
        if search:
            vendors = vendors.filter(
                Q(name__icontains=search)
                | Q(contact_person__icontains=search)
                | Q(phone__icontains=search)
            )

        pagination, data = paginate_queryset(vendors, request, VendorSerializer)
        if pagination:
            return Response({"results": data, "pagination": pagination})
        return Response(data)

    def post(self, request):
        serializer = VendorSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        name = serializer.validated_data.get("name", "").strip()
        if Vendor.objects.filter(
            restaurant=request.restaurant, name=name, is_deleted=False
        ).exists():
            return Response(
                {"error": f"A vendor named '{name}' already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save(restaurant=request.restaurant, updated_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@method_decorator(manager_or_above_required, name="get")
@method_decorator(manager_or_above_required, name="put")
@method_decorator(owner_required, name="delete")
class VendorDetailAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        vendor = Vendor.get_vendor_by_id(pk, request.restaurant)
        if not vendor:
            return Response(
                {"error": "Vendor not found"}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(VendorSerializer(vendor).data)

    def put(self, request, pk):
        vendor = Vendor.get_vendor_by_id(pk, request.restaurant)
        if not vendor:
            return Response(
                {"error": "Vendor not found"}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = VendorSerializer(vendor, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)

    def delete(self, request, pk):
        vendor = Vendor.get_vendor_by_id(pk, request.restaurant)
        if not vendor:
            return Response(
                {"error": "Vendor not found"}, status=status.HTTP_404_NOT_FOUND
            )
        vendor.soft_delete(request.user)
        return Response({"success": True})
