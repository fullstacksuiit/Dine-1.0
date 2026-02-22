from datetime import date
from decimal import Decimal
from django.db import models
from purchase.models.purchase_order import PurchaseOrder
from purchase.models.purchase_invoice import PurchaseInvoice
from purchase.models.inventory_item import InventoryItem
from purchase.models.expense import Expense
from .stock_service import StockService
from .payment_service import PaymentService


class FinanceSummaryService:

    @classmethod
    def get_dashboard_summary(cls, restaurant):
        """
        Returns a finance summary dict for the dashboard.
        """
        today = date.today()
        month_start = today.replace(day=1)

        # Accounts payable & receivable
        total_payable = PaymentService.get_total_accounts_payable(restaurant)
        total_receivable = PaymentService.get_total_accounts_receivable(restaurant)

        # Stock
        total_stock_value = StockService.get_total_stock_value(restaurant)
        low_stock_count = InventoryItem.get_low_stock_items(restaurant).count()

        # Purchase orders
        pending_pos = PurchaseOrder.objects.filter(
            restaurant=restaurant,
            is_deleted=False,
            status__in=[
                PurchaseOrder.Status.DRAFT.value,
                PurchaseOrder.Status.APPROVED.value,
            ],
        ).count()

        # Unpaid invoices
        unpaid_invoices = PurchaseInvoice.objects.filter(
            restaurant=restaurant,
            is_deleted=False,
            status__in=[
                PurchaseInvoice.Status.PENDING.value,
                PurchaseInvoice.Status.PARTIALLY_PAID.value,
            ],
        ).count()

        # Monthly expenses
        monthly_expenses = Expense.objects.filter(
            restaurant=restaurant,
            is_deleted=False,
            expense_date__gte=month_start,
            expense_date__lte=today,
        ).aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0.00")

        # Expenses by category this month
        expenses_by_category = (
            Expense.objects.filter(
                restaurant=restaurant,
                is_deleted=False,
                expense_date__gte=month_start,
                expense_date__lte=today,
            )
            .values("category__name")
            .annotate(total=models.Sum("amount"))
            .order_by("-total")
        )
        category_breakdown = [
            {
                "category": row["category__name"] or "Uncategorized",
                "amount": row["total"],
            }
            for row in expenses_by_category
        ]

        return {
            "total_accounts_payable": total_payable,
            "total_accounts_receivable": total_receivable,
            "total_stock_value": total_stock_value,
            "low_stock_items_count": low_stock_count,
            "pending_purchase_orders_count": pending_pos,
            "unpaid_invoices_count": unpaid_invoices,
            "total_expenses_this_month": monthly_expenses,
            "expenses_by_category": category_breakdown,
        }
