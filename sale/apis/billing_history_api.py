from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Avg, Sum, Count, Q

from sale.models import Bill
from sale.serializers import BillSerializer
from sale.services.reporting_service import ReportingService
from common.decorators import waiter_or_above_required, subscription_required
from common.pagination import StandardPagination


@method_decorator(subscription_required, name="dispatch")
@method_decorator(waiter_or_above_required, name="get")
class BillingHistoryAPIView(APIView):
    """
    API endpoint for billing history with filtering capabilities
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get filtered billing history
        Query parameters:
        - from: Start date (YYYY-MM-DD)
        - to: End date (YYYY-MM-DD)
        - order_type: Filter by order type (RESTAURANT, SWIGGY, ZOMATO, ALL)
        - payment_type: Filter by payment type (CASH, CARD, UPI, Non Paid, ALL)
        - payment_status: Filter by payment status (UNPAID, PAID, ALL)
        - search: Search by invoice number, table, customer name, or contact
        - page: Page number (opt-in; omit for all results)
        - page_size: Results per page (default 50, max 200)
        """
        start_date = request.query_params.get('from')
        end_date = request.query_params.get('to')
        order_type = request.query_params.get('order_type', 'ALL')
        payment_type = request.query_params.get('payment_type', 'ALL')
        payment_status = request.query_params.get('payment_status', 'ALL')
        search = request.query_params.get('search', '').strip()

        try:
            # Use the existing ReportingService to get filtered bills
            if start_date and end_date:
                bills = ReportingService.get_filtered_invoices(
                    start_date, end_date, order_type, payment_type, request.restaurant
                )
            else:
                # Get bills for today if no date range provided
                bills = Bill.get_bills_for_today(request.restaurant)

            # Filter only completed bills with amount > 0
            bills = bills.filter(active=False, amount__gt=0, is_deleted=False)

            if payment_status and payment_status != 'ALL':
                bills = bills.filter(payment_status=payment_status)

            # Server-side search
            if search:
                bills = bills.filter(
                    Q(invoice_number__icontains=search) |
                    Q(table_number__icontains=search) |
                    Q(customer_name__icontains=search) |
                    Q(contact__icontains=search)
                )

            bills = bills.order_by('-updated_at')

            # Summary is computed on the FULL filtered queryset (not paginated)
            summary_stats = bills.aggregate(
                total_sale=Sum('amount'),
                avg_sale=Avg('amount'),
                count=Count('id'),
                unpaid_count=Count('id', filter=Q(payment_status='UNPAID')),
                unpaid_total=Sum('amount', filter=Q(payment_status='UNPAID')),
            )

            payment_type_totals = (
                bills.values('payment_type')
                .order_by('payment_type')
                .annotate(total_amount=Sum('amount'))
            )

            # Paginate if ?page= is provided (opt-in, backward compatible)
            pagination_meta = None
            page_param = request.query_params.get('page')
            if page_param:
                paginator = StandardPagination()
                paginated_bills = paginator.paginate_queryset(bills, request)
                bills_data = BillSerializer(paginated_bills, many=True).data
                pagination_meta = {
                    'count': paginator.page.paginator.count,
                    'num_pages': paginator.page.paginator.num_pages,
                    'current_page': paginator.page.number,
                    'page_size': paginator.get_page_size(request),
                }
            else:
                bills_data = BillSerializer(bills, many=True).data

            # Prepare response
            response_data = {
                'bills': bills_data,
                'summary': {
                    'total_sale': round(summary_stats['total_sale'] or 0, 2),
                    'avg': round(summary_stats['avg_sale'] or 0, 2),
                    'count': summary_stats['count'],
                    'payment_type_totals': list(payment_type_totals),
                    'unpaid_count': summary_stats['unpaid_count'],
                    'unpaid_total': round(summary_stats['unpaid_total'] or 0, 2),
                },
                'pagination': pagination_meta,
                'filters': {
                    'from': start_date,
                    'to': end_date,
                    'order_type': order_type,
                    'payment_type': payment_type,
                    'payment_status': payment_status,
                    'search': search,
                }
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': f'Failed to fetch billing history: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
