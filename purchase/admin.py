from django.contrib import admin
from purchase.models import (
    Vendor,
    Customer,
    ExpenseCategory,
    InventoryItem,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseInvoice,
    PurchaseInvoiceItem,
    StockEntry,
    Payment,
    Expense,
)


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "gstin", "city", "restaurant")
    list_filter = ("restaurant",)
    search_fields = ("name", "phone", "gstin")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "credit_limit", "opening_balance", "restaurant")
    list_filter = ("restaurant",)
    search_fields = ("name", "phone")


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "restaurant")
    list_filter = ("restaurant",)


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("name", "unit", "current_stock", "low_stock_threshold", "cost_per_unit", "restaurant")
    list_filter = ("unit", "restaurant")
    search_fields = ("name",)


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "vendor", "status", "total_amount", "order_date", "restaurant")
    list_filter = ("status", "restaurant")
    search_fields = ("order_number", "vendor__name")
    ordering = ("-order_date",)


@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = ("item_name", "quantity", "unit_price", "amount", "purchase_order")


@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "vendor", "status", "total_amount", "amount_paid", "invoice_date", "restaurant")
    list_filter = ("status", "restaurant")
    search_fields = ("invoice_number", "vendor__name")
    ordering = ("-invoice_date",)


@admin.register(PurchaseInvoiceItem)
class PurchaseInvoiceItemAdmin(admin.ModelAdmin):
    list_display = ("item_name", "quantity", "unit_price", "amount", "purchase_invoice")


@admin.register(StockEntry)
class StockEntryAdmin(admin.ModelAdmin):
    list_display = ("inventory_item", "entry_type", "quantity", "unit_cost", "entry_date", "restaurant")
    list_filter = ("entry_type", "restaurant")
    ordering = ("-entry_date",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("payment_type", "amount", "payment_mode", "payment_date", "vendor", "customer", "restaurant")
    list_filter = ("payment_type", "payment_mode", "restaurant")
    ordering = ("-payment_date",)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("description", "amount", "category", "expense_date", "payment_mode", "restaurant")
    list_filter = ("category", "payment_mode", "restaurant")
    ordering = ("-expense_date",)
