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
from purchase.models.customer import Customer
from purchase.models.payment import Payment
from purchase.serializers import CustomerSerializer, PaymentSerializer
from purchase.services.payment_service import PaymentService


@method_decorator(waiter_or_above_required, name="get")
@method_decorator(manager_or_above_required, name="post")
class CustomerListCreateAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        customers = Customer.get_customers_for_restaurant(request.restaurant)

        search = request.query_params.get("search", "").strip()
        if search:
            customers = customers.filter(
                Q(name__icontains=search)
                | Q(phone__icontains=search)
                | Q(email__icontains=search)
            )

        pagination, data = paginate_queryset(customers, request, CustomerSerializer)
        if pagination:
            return Response({"results": data, "pagination": pagination})
        return Response(data)

    def post(self, request):
        serializer = CustomerSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone = serializer.validated_data.get("phone", "").strip()
        if Customer.objects.filter(
            restaurant=request.restaurant, phone=phone, is_deleted=False
        ).exists():
            return Response(
                {"error": f"A customer with phone '{phone}' already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save(restaurant=request.restaurant, updated_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@method_decorator(waiter_or_above_required, name="get")
@method_decorator(manager_or_above_required, name="put")
@method_decorator(owner_required, name="delete")
class CustomerDetailAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        customer = Customer.get_customer_by_id(pk, request.restaurant)
        if not customer:
            return Response(
                {"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(CustomerSerializer(customer).data)

    def put(self, request, pk):
        customer = Customer.get_customer_by_id(pk, request.restaurant)
        if not customer:
            return Response(
                {"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = CustomerSerializer(customer, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)

    def delete(self, request, pk):
        customer = Customer.get_customer_by_id(pk, request.restaurant)
        if not customer:
            return Response(
                {"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND
            )
        customer.soft_delete(request.user)
        return Response({"success": True})


@method_decorator(manager_or_above_required, name="dispatch")
class CustomerOutstandingAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        customer = Customer.get_customer_by_id(pk, request.restaurant)
        if not customer:
            return Response(
                {"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND
            )

        outstanding = PaymentService.get_customer_outstanding(
            customer, request.restaurant
        )
        payments = Payment.get_payments_for_customer(pk, request.restaurant)

        return Response(
            {
                "customer": CustomerSerializer(customer).data,
                "outstanding_balance": outstanding,
                "payments": PaymentSerializer(payments, many=True).data,
            }
        )
