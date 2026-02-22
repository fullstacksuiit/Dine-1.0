from django.contrib import admin
from sale.models import Dish, Bill, Order, KOT, Course, Menu

# Register your models here.
admin.site.register([Dish, Order, KOT, Course, Menu])

from .models import Bill


class BillAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "invoice_number",
        "restaurant",
        "created_at",
        "is_deleted",
        "active",
        "is_takeaway",
        "table_number",
    )
    list_filter = ("restaurant", "is_deleted")
    search_fields = (
        "invoice_number",
        "restaurant__name",
        "table_number",
        "customer_name",
        "contact",
    )
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")


admin.site.register(Bill, BillAdmin)
