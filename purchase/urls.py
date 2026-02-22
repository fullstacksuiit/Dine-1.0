from django.urls import path
from purchase.apis.vendor_api import VendorListCreateAPI, VendorDetailAPI
from purchase.apis.customer_api import (
    CustomerListCreateAPI,
    CustomerDetailAPI,
    CustomerOutstandingAPI,
)
from purchase.apis.purchase_order_api import (
    PurchaseOrderListCreateAPI,
    PurchaseOrderDetailAPI,
    PurchaseOrderActionAPI,
)
from purchase.apis.purchase_invoice_api import (
    PurchaseInvoiceListCreateAPI,
    PurchaseInvoiceDetailAPI,
)
from purchase.apis.inventory_api import (
    InventoryListCreateAPI,
    InventoryDetailAPI,
    LowStockAPI,
    StockEntryCreateAPI,
)
from purchase.apis.payment_api import PaymentListCreateAPI, PaymentDetailAPI
from purchase.apis.expense_api import (
    ExpenseCategoryListCreateAPI,
    ExpenseCategoryDetailAPI,
    ExpenseListCreateAPI,
    ExpenseDetailAPI,
)
from purchase.apis.dashboard_api import FinanceDashboardAPI
from purchase.apis.inventory_excel_api import InventoryExportAPI, InventoryImportAPI
from purchase.apis.reporting_api import ExpenseReportAPI, PurchaseSummaryReportAPI
from purchase import views

# HTML views
view_urlpatterns = [
    path("", views.purchase_dashboard, name="purchase_dashboard"),
    path("vendors/", views.vendors_view, name="purchase_vendors"),
    path("customers/", views.customers_view, name="purchase_customers"),
    path("inventory/", views.inventory_view, name="purchase_inventory"),
    path("orders/", views.purchase_orders_view, name="purchase_orders"),
    path("invoices/", views.purchase_invoices_view, name="purchase_invoices"),
    path("expenses/", views.expenses_view, name="purchase_expenses"),
    path("payments/", views.payments_view, name="purchase_payments"),
]

# API endpoints
api_urlpatterns = [
    # Vendors
    path("api/vendors/", VendorListCreateAPI.as_view(), name="api_vendor_list_create"),
    path("api/vendors/<uuid:pk>", VendorDetailAPI.as_view(), name="api_vendor_detail"),

    # Customers
    path("api/customers/", CustomerListCreateAPI.as_view(), name="api_customer_list_create"),
    path("api/customers/<uuid:pk>", CustomerDetailAPI.as_view(), name="api_customer_detail"),
    path("api/customers/<uuid:pk>/outstanding/", CustomerOutstandingAPI.as_view(), name="api_customer_outstanding"),

    # Purchase Orders
    path("api/purchase-orders/", PurchaseOrderListCreateAPI.as_view(), name="api_po_list_create"),
    path("api/purchase-orders/<uuid:pk>", PurchaseOrderDetailAPI.as_view(), name="api_po_detail"),
    path("api/purchase-orders/<uuid:pk>/<str:action>/", PurchaseOrderActionAPI.as_view(), name="api_po_action"),

    # Purchase Invoices
    path("api/purchase-invoices/", PurchaseInvoiceListCreateAPI.as_view(), name="api_pi_list_create"),
    path("api/purchase-invoices/<uuid:pk>", PurchaseInvoiceDetailAPI.as_view(), name="api_pi_detail"),

    # Inventory
    path("api/inventory/", InventoryListCreateAPI.as_view(), name="api_inventory_list_create"),
    path("api/inventory/low-stock/", LowStockAPI.as_view(), name="api_inventory_low_stock"),
    path("api/inventory/<uuid:pk>", InventoryDetailAPI.as_view(), name="api_inventory_detail"),
    path("api/inventory/<uuid:pk>/stock-entry/", StockEntryCreateAPI.as_view(), name="api_stock_entry_create"),

    # Payments
    path("api/payments/", PaymentListCreateAPI.as_view(), name="api_payment_list_create"),
    path("api/payments/<uuid:pk>", PaymentDetailAPI.as_view(), name="api_payment_detail"),

    # Expenses
    path("api/expense-categories/", ExpenseCategoryListCreateAPI.as_view(), name="api_expense_category_list_create"),
    path("api/expense-categories/<uuid:pk>", ExpenseCategoryDetailAPI.as_view(), name="api_expense_category_detail"),
    path("api/expenses/", ExpenseListCreateAPI.as_view(), name="api_expense_list_create"),
    path("api/expenses/<uuid:pk>", ExpenseDetailAPI.as_view(), name="api_expense_detail"),

    # Dashboard
    path("api/dashboard/summary/", FinanceDashboardAPI.as_view(), name="api_finance_dashboard"),

    # Inventory Excel
    path("api/inventory/export/", InventoryExportAPI.as_view(), name="api_inventory_export"),
    path("api/inventory/import/", InventoryImportAPI.as_view(), name="api_inventory_import"),

    # Reports
    path("api/reports/expenses/", ExpenseReportAPI.as_view(), name="api_expense_report"),
    path("api/reports/purchases/", PurchaseSummaryReportAPI.as_view(), name="api_purchase_summary_report"),
]

urlpatterns = view_urlpatterns + api_urlpatterns
