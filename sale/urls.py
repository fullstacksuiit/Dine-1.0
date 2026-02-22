from django.urls import path
from sale import views
from sale.apis import DishListCreateAPIView, DishDetailUpdateDeleteAPIView
from sale.apis.courses_api import CourseListCreateAPIView, CourseDetailUpdateDeleteAPIView
from sale.apis.menu_api import MenuAPIView
from sale.apis.public_menu_qr_api import PublicMenuQRAPIView
from sale.apis.dishes_api import DishExportAPIView, DishImportAPIView, PopularDishesAPIView
from sale.apis.order_api import OrderAPI
from sale.apis.bill_api import BillApi, BillMergeApi, BillSettleApi, bill_kot_status_api
from sale.apis.kot_api import KOTApi
from sale.apis.loyalty_api import CustomerLoyaltyAPIView, RestaurantLoyaltySummaryAPIView
from sale.apis.billing_history_api import BillingHistoryAPIView

# API endpoints
api_urlpatterns = [
    path("api/dishes/", DishListCreateAPIView.as_view(), name="api_dishes_list_create"),
    path("api/dishes/download/", DishExportAPIView.as_view(), name="dishes_export"),
    path("api/dishes/upload/", DishImportAPIView.as_view(), name="dishes_import"),
    path("api/dishes/popular/", PopularDishesAPIView.as_view(), name="api_popular_dishes"),
    path("api/dishes/<uuid:id>", DishDetailUpdateDeleteAPIView.as_view(), name="api_dish_detail"),
    path("api/courses/", CourseListCreateAPIView.as_view(), name="api_courses_list_create"),
    path("api/courses/<uuid:id>", CourseDetailUpdateDeleteAPIView.as_view(), name="api_course_detail"),
    path("api/menu/", MenuAPIView.as_view(), name="api_menu_ordering"),
    path("api/public-menu-qr/", PublicMenuQRAPIView.as_view(), name="api_public_menu_qr"),
    path("api/orders/", OrderAPI.as_view(), name="api_orders"),
    path("api/orders/<uuid:order_id>", OrderAPI.as_view(), name="api_orders"),
    path("api/bills/", BillApi.as_view(), name="api_bills_list_create"),
    path("api/bills/<uuid:pk>", BillApi.as_view(), name="api_bills_detail"),
    path("api/bills/<uuid:pk>/settle/", BillSettleApi.as_view(), name="api_bills_settle"),
    path("api/bills/<uuid:pk>/merge/", BillMergeApi.as_view(), name="api_bills_merge"),
    path("api/kots/", KOTApi.as_view(), name="api_kots_list_create"),
    path("api/kots/<uuid:pk>", KOTApi.as_view(), name="api_kots_detail"),
    path("api/bill-status/<uuid:restaurant_id>", bill_kot_status_api, name="api_bill_status"),
    path("api/billing-history/", BillingHistoryAPIView.as_view(), name="api_billing_history"),
    path("api/customer-loyalty/", CustomerLoyaltyAPIView.as_view(), name="api_customer_loyalty"),
    path("api/loyalty-summary/", RestaurantLoyaltySummaryAPIView.as_view(), name="api_loyalty_summary"),
]

# HTML/template-based views
view_urlpatterns = [
    path("bill/form", views.bill_form, name="bill_form"),
    path("invoice/<uuid:bill_id>", views.invoice, name="invoice"),
    path("menu/", views.menu, name="menu"),
    path("order-menu/", views.order_menu, name="order_menu"),
    path("history/", views.sale_history, name="sale_history"),
    path("report/", views.report, name="report"),
    path("kot/active", views.kot_history, name="kot_history"),
    path("kot/<uuid:kot_id>", views.kot, name="kot"),
    path("public/menu/<uuid:restaurant_id>", views.public_menu, name="public_menu"),
    path("settings/", views.settings, name="settings"),
    path("takeaway-order/", views.takeaway_order_view, name="takeaway_order"),
    path("order-status/<uuid:restaurant_id>", views.order_status_view, name="order_status"),
    path("home/", views.home, name="home"),
    path("", views.order_view, name="order"),
]

urlpatterns = view_urlpatterns + api_urlpatterns
