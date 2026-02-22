from rest_framework import serializers
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


class VendorSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)

    class Meta:
        model = Vendor
        exclude = ("restaurant", "updated_by", "is_deleted")


class VendorMinimalSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)

    class Meta:
        model = Vendor
        fields = ["id", "name", "phone", "gstin"]


class CustomerSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)

    class Meta:
        model = Customer
        exclude = ("restaurant", "updated_by", "is_deleted")


class ExpenseCategorySerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)

    class Meta:
        model = ExpenseCategory
        exclude = ("restaurant", "updated_by", "is_deleted")


class InventoryItemSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    stock_value = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    category_name = serializers.CharField(
        source="category.name", read_only=True, default=None
    )

    class Meta:
        model = InventoryItem
        exclude = ("restaurant", "updated_by", "is_deleted")


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)

    class Meta:
        model = PurchaseOrderItem
        exclude = ("updated_by", "is_deleted")


class PurchaseOrderSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    vendor = VendorMinimalSerializer(read_only=True)
    items = PurchaseOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseOrder
        exclude = ("restaurant", "updated_by", "is_deleted")


class PurchaseOrderListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views (without items)."""
    id = serializers.CharField(read_only=True)
    vendor = VendorMinimalSerializer(read_only=True)

    class Meta:
        model = PurchaseOrder
        exclude = ("restaurant", "updated_by", "is_deleted")


class PurchaseInvoiceItemSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)

    class Meta:
        model = PurchaseInvoiceItem
        exclude = ("updated_by", "is_deleted")


class PurchaseInvoiceSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    vendor = VendorMinimalSerializer(read_only=True)
    balance_due = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    items = PurchaseInvoiceItemSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseInvoice
        exclude = ("restaurant", "updated_by", "is_deleted")


class PurchaseInvoiceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views (without items)."""
    id = serializers.CharField(read_only=True)
    vendor = VendorMinimalSerializer(read_only=True)
    balance_due = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = PurchaseInvoice
        exclude = ("restaurant", "updated_by", "is_deleted")


class StockEntrySerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    item_name = serializers.CharField(
        source="inventory_item.name", read_only=True
    )

    class Meta:
        model = StockEntry
        exclude = ("restaurant", "updated_by", "is_deleted")


class PaymentSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    vendor_name = serializers.CharField(
        source="vendor.name", read_only=True, default=None
    )
    customer_name = serializers.CharField(
        source="customer.name", read_only=True, default=None
    )

    class Meta:
        model = Payment
        exclude = ("restaurant", "updated_by", "is_deleted")


class ExpenseSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    category_name = serializers.CharField(
        source="category.name", read_only=True, default=None
    )
    vendor_name = serializers.CharField(
        source="vendor.name", read_only=True, default=None
    )

    class Meta:
        model = Expense
        exclude = ("restaurant", "updated_by", "is_deleted")
