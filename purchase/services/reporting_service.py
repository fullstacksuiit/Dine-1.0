from datetime import date, timedelta
from decimal import Decimal
from django.db import models
from purchase.models.expense import Expense
from purchase.models.purchase_invoice import PurchaseInvoice
from purchase.models.purchase_order import PurchaseOrder
from purchase.models.payment import Payment


class ReportingService:

    @classmethod
    def get_expense_report(cls, restaurant, start_date, end_date):
        """
        Returns expense breakdown for the given date range.
        """
        qs = Expense.objects.filter(
            restaurant=restaurant,
            is_deleted=False,
            expense_date__gte=start_date,
            expense_date__lte=end_date,
        )

        total = qs.aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")

        # By category
        by_category = list(
            qs.values("category__name")
            .annotate(total=models.Sum("amount"), count=models.Count("id"))
            .order_by("-total")
        )
        category_breakdown = [
            {
                "category": row["category__name"] or "Uncategorized",
                "amount": row["total"],
                "count": row["count"],
            }
            for row in by_category
        ]

        # By payment mode
        by_mode = list(
            qs.values("payment_mode")
            .annotate(total=models.Sum("amount"), count=models.Count("id"))
            .order_by("-total")
        )
        mode_breakdown = [
            {
                "payment_mode": row["payment_mode"],
                "amount": row["total"],
                "count": row["count"],
            }
            for row in by_mode
        ]

        # By vendor (top 10)
        by_vendor = list(
            qs.exclude(vendor__isnull=True)
            .values("vendor__name")
            .annotate(total=models.Sum("amount"), count=models.Count("id"))
            .order_by("-total")[:10]
        )
        vendor_breakdown = [
            {
                "vendor": row["vendor__name"],
                "amount": row["total"],
                "count": row["count"],
            }
            for row in by_vendor
        ]

        # Daily totals
        daily = list(
            qs.values("expense_date")
            .annotate(total=models.Sum("amount"))
            .order_by("expense_date")
        )
        daily_breakdown = [
            {"date": str(row["expense_date"]), "amount": row["total"]}
            for row in daily
        ]

        return {
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_expenses": total,
            "expense_count": qs.count(),
            "by_category": category_breakdown,
            "by_payment_mode": mode_breakdown,
            "by_vendor": vendor_breakdown,
            "daily_breakdown": daily_breakdown,
        }

    @classmethod
    def get_monthly_expense_report(cls, restaurant, year, month):
        """Convenience wrapper for monthly reports."""
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        return cls.get_expense_report(restaurant, start_date, end_date)

    @classmethod
    def get_weekly_expense_report(cls, restaurant, week_ending):
        """
        Report for 7-day period ending on week_ending (inclusive).
        """
        start_date = week_ending - timedelta(days=6)
        return cls.get_expense_report(restaurant, start_date, week_ending)

    @classmethod
    def get_purchase_summary(cls, restaurant, start_date, end_date):
        """
        Purchase summary for the given date range including
        invoices, orders, and payments.
        """
        # Purchase orders
        orders = PurchaseOrder.objects.filter(
            restaurant=restaurant,
            is_deleted=False,
            order_date__gte=start_date,
            order_date__lte=end_date,
        )
        orders_by_status = list(
            orders.values("status")
            .annotate(count=models.Count("id"), total=models.Sum("total_amount"))
            .order_by("status")
        )

        # Purchase invoices
        invoices = PurchaseInvoice.objects.filter(
            restaurant=restaurant,
            is_deleted=False,
            invoice_date__gte=start_date,
            invoice_date__lte=end_date,
        )
        total_invoiced = invoices.aggregate(
            total=models.Sum("total_amount")
        )["total"] or Decimal("0.00")
        total_paid = invoices.aggregate(
            total=models.Sum("amount_paid")
        )["total"] or Decimal("0.00")

        invoices_by_status = list(
            invoices.values("status")
            .annotate(count=models.Count("id"), total=models.Sum("total_amount"))
            .order_by("status")
        )

        # Top vendors by invoice amount
        top_vendors = list(
            invoices.values("vendor__name")
            .annotate(total=models.Sum("total_amount"), count=models.Count("id"))
            .order_by("-total")[:10]
        )

        # Payments in period
        payments = Payment.objects.filter(
            restaurant=restaurant,
            is_deleted=False,
            payment_date__gte=start_date,
            payment_date__lte=end_date,
        )
        vendor_payments = payments.filter(
            payment_type=Payment.PaymentType.VENDOR_PAYMENT.value
        ).aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")
        customer_receipts = payments.filter(
            payment_type=Payment.PaymentType.CUSTOMER_RECEIPT.value
        ).aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")

        return {
            "start_date": str(start_date),
            "end_date": str(end_date),
            "purchase_orders": {
                "total_count": orders.count(),
                "by_status": [
                    {
                        "status": row["status"],
                        "count": row["count"],
                        "total": row["total"] or Decimal("0.00"),
                    }
                    for row in orders_by_status
                ],
            },
            "purchase_invoices": {
                "total_count": invoices.count(),
                "total_invoiced": total_invoiced,
                "total_paid": total_paid,
                "balance_due": total_invoiced - total_paid,
                "by_status": [
                    {
                        "status": row["status"],
                        "count": row["count"],
                        "total": row["total"] or Decimal("0.00"),
                    }
                    for row in invoices_by_status
                ],
            },
            "top_vendors": [
                {"vendor": row["vendor__name"], "total": row["total"], "count": row["count"]}
                for row in top_vendors
            ],
            "payments": {
                "vendor_payments": vendor_payments,
                "customer_receipts": customer_receipts,
            },
        }
