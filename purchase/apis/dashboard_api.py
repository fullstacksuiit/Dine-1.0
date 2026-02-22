from django.core.cache import cache
from django.utils.decorators import method_decorator
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from common.decorators import manager_or_above_required
from purchase.services.finance_summary_service import FinanceSummaryService


@method_decorator(manager_or_above_required, name="dispatch")
class FinanceDashboardAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cache_key = f"finance_dashboard_{request.restaurant.id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        summary = FinanceSummaryService.get_dashboard_summary(request.restaurant)
        cache.set(cache_key, summary, timeout=120)
        return Response(summary)
