from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

from common.permissions import IsOwnerOrManager
from sale.services.qr_service import QRService

class PublicMenuQRAPIView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated, IsOwnerOrManager]

    def get(self, request):
        restaurant = request.restaurant
        url = request.build_absolute_uri(f"/sale/public/menu/{restaurant.id}")
        buf = QRService.generate_qr_for_url(url, restaurant.display_name)
        buf.seek(0)  # Reset the buffer position to the beginning
        return HttpResponse(buf, content_type='image/png')
