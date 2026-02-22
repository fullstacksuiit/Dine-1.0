from decimal import Decimal
from django.db.models import Q
from django.utils.decorators import method_decorator
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.decorators import manager_or_above_required, owner_required
from common.pagination import paginate_queryset
from purchase.models.expense_category import ExpenseCategory
from purchase.models.expense import Expense
from purchase.serializers import ExpenseCategorySerializer, ExpenseSerializer


@method_decorator(manager_or_above_required, name="dispatch")
class ExpenseCategoryListCreateAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        categories = ExpenseCategory.get_categories_for_restaurant(request.restaurant)
        return Response(ExpenseCategorySerializer(categories, many=True).data)

    def post(self, request):
        serializer = ExpenseCategorySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        name = serializer.validated_data.get("name", "").strip()
        if ExpenseCategory.objects.filter(
            restaurant=request.restaurant, name=name, is_deleted=False
        ).exists():
            return Response(
                {"error": f"Category '{name}' already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save(restaurant=request.restaurant, updated_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@method_decorator(manager_or_above_required, name="put")
@method_decorator(owner_required, name="delete")
class ExpenseCategoryDetailAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, pk):
        try:
            category = ExpenseCategory.objects.get(
                id=pk, restaurant=request.restaurant, is_deleted=False
            )
        except ExpenseCategory.DoesNotExist:
            return Response(
                {"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = ExpenseCategorySerializer(
            category, data=request.data, partial=True
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)

    def delete(self, request, pk):
        try:
            category = ExpenseCategory.objects.get(
                id=pk, restaurant=request.restaurant, is_deleted=False
            )
        except ExpenseCategory.DoesNotExist:
            return Response(
                {"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND
            )
        category.soft_delete(request.user)
        return Response({"success": True})


@method_decorator(manager_or_above_required, name="dispatch")
class ExpenseListCreateAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        category_id = request.query_params.get("category_id")
        category = None
        if category_id:
            try:
                category = ExpenseCategory.objects.get(
                    id=category_id,
                    restaurant=request.restaurant,
                    is_deleted=False,
                )
            except ExpenseCategory.DoesNotExist:
                pass

        expenses = Expense.get_expenses_for_restaurant(
            request.restaurant, category=category
        )

        search = request.query_params.get("search", "").strip()
        if search:
            expenses = expenses.filter(
                Q(description__icontains=search)
                | Q(vendor__name__icontains=search)
                | Q(category__name__icontains=search)
            )

        pagination, data = paginate_queryset(expenses, request, ExpenseSerializer)
        if pagination:
            return Response({"results": data, "pagination": pagination})
        return Response(data)

    def post(self, request):
        data = request.data
        category = None
        if data.get("category_id"):
            try:
                category = ExpenseCategory.objects.get(
                    id=data["category_id"],
                    restaurant=request.restaurant,
                    is_deleted=False,
                )
            except ExpenseCategory.DoesNotExist:
                return Response(
                    {"error": "Category not found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        vendor = None
        if data.get("vendor_id"):
            from purchase.models.vendor import Vendor

            vendor = Vendor.get_vendor_by_id(
                data["vendor_id"], request.restaurant
            )

        expense = Expense.objects.create(
            restaurant=request.restaurant,
            category=category,
            vendor=vendor,
            description=data.get("description", ""),
            amount=Decimal(str(data.get("amount", 0))),
            expense_date=data.get("expense_date"),
            payment_mode=data.get("payment_mode", "CASH"),
            reference_number=data.get("reference_number"),
            notes=data.get("notes"),
            updated_by=request.user,
        )
        return Response(ExpenseSerializer(expense).data, status=status.HTTP_201_CREATED)


@method_decorator(manager_or_above_required, name="get")
@method_decorator(manager_or_above_required, name="put")
@method_decorator(owner_required, name="delete")
class ExpenseDetailAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            expense = Expense.objects.select_related("category", "vendor").get(
                id=pk, restaurant=request.restaurant, is_deleted=False
            )
        except Expense.DoesNotExist:
            return Response(
                {"error": "Expense not found"}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(ExpenseSerializer(expense).data)

    def put(self, request, pk):
        try:
            expense = Expense.objects.get(
                id=pk, restaurant=request.restaurant, is_deleted=False
            )
        except Expense.DoesNotExist:
            return Response(
                {"error": "Expense not found"}, status=status.HTTP_404_NOT_FOUND
            )

        data = request.data
        for field in ["description", "expense_date", "payment_mode", "reference_number", "notes"]:
            if field in data:
                setattr(expense, field, data[field])

        if "amount" in data:
            expense.amount = Decimal(str(data["amount"]))

        if "category_id" in data:
            if data["category_id"]:
                try:
                    expense.category = ExpenseCategory.objects.get(
                        id=data["category_id"],
                        restaurant=request.restaurant,
                        is_deleted=False,
                    )
                except ExpenseCategory.DoesNotExist:
                    pass
            else:
                expense.category = None

        expense.updated_by = request.user
        expense.save()
        return Response(ExpenseSerializer(expense).data)

    def delete(self, request, pk):
        try:
            expense = Expense.objects.get(
                id=pk, restaurant=request.restaurant, is_deleted=False
            )
        except Expense.DoesNotExist:
            return Response(
                {"error": "Expense not found"}, status=status.HTTP_404_NOT_FOUND
            )
        expense.soft_delete(request.user)
        return Response({"success": True})
