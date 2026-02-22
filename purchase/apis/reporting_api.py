from datetime import date, datetime
from django.utils.decorators import method_decorator
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.decorators import manager_or_above_required
from purchase.services.reporting_service import ReportingService


@method_decorator(manager_or_above_required, name="dispatch")
class ExpenseReportAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        GET /purchase/api/reports/expenses/?period=monthly&year=2026&month=2
        GET /purchase/api/reports/expenses/?period=weekly&week_ending=2026-02-22
        GET /purchase/api/reports/expenses/?start_date=2026-01-01&end_date=2026-02-28
        """
        period = request.query_params.get("period")

        if period == "monthly":
            try:
                year = int(request.query_params.get("year", date.today().year))
                month = int(request.query_params.get("month", date.today().month))
            except (ValueError, TypeError):
                return Response(
                    {"error": "Invalid year or month"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            data = ReportingService.get_monthly_expense_report(
                request.restaurant, year, month
            )
        elif period == "weekly":
            week_ending = request.query_params.get("week_ending")
            if week_ending:
                try:
                    week_ending = datetime.strptime(week_ending, "%Y-%m-%d").date()
                except ValueError:
                    return Response(
                        {"error": "Invalid date format. Use YYYY-MM-DD"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                week_ending = date.today()
            data = ReportingService.get_weekly_expense_report(
                request.restaurant, week_ending
            )
        else:
            # Custom date range
            start_date_str = request.query_params.get("start_date")
            end_date_str = request.query_params.get("end_date")
            try:
                start_date = (
                    datetime.strptime(start_date_str, "%Y-%m-%d").date()
                    if start_date_str
                    else date.today().replace(day=1)
                )
                end_date = (
                    datetime.strptime(end_date_str, "%Y-%m-%d").date()
                    if end_date_str
                    else date.today()
                )
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            data = ReportingService.get_expense_report(
                request.restaurant, start_date, end_date
            )

        return Response(data)


@method_decorator(manager_or_above_required, name="dispatch")
class PurchaseSummaryReportAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        GET /purchase/api/reports/purchases/?start_date=2026-01-01&end_date=2026-02-28
        """
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")
        try:
            start_date = (
                datetime.strptime(start_date_str, "%Y-%m-%d").date()
                if start_date_str
                else date.today().replace(day=1)
            )
            end_date = (
                datetime.strptime(end_date_str, "%Y-%m-%d").date()
                if end_date_str
                else date.today()
            )
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = ReportingService.get_purchase_summary(
            request.restaurant, start_date, end_date
        )
        return Response(data)
