from rest_framework import serializers

from sale.models import Bill, Order, Dish
from sale.models.course import Course
from sale.models.kot import KOT


class KOTStatusField(serializers.CharField):
    """Custom field to handle KOT status conversion between enum names and values."""

    def to_representation(self, value):
        """Convert status value to enum name for output."""
        try:
            # Find the enum member that has this value
            for status_enum in KOT.Status:
                if status_enum.value == value:
                    return status_enum.name
            return value  # Fallback to original value if not found
        except:
            return value

    def to_internal_value(self, data):
        """Convert enum name to status value for saving."""
        try:
            # Check if the input is an enum name, convert to value
            if hasattr(KOT.Status, data):
                return getattr(KOT.Status, data).value
            # If it's already a value, return as is
            return data
        except:
            return data


class CourseSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)

    class Meta:
        model = Course
        fields = ["id", "name"]
        read_only_fields = ["id", "restaurant"]


class BillMinimalSerializer(serializers.ModelSerializer):
    """Lightweight bill serializer for nested use (e.g., inside KOT responses)."""
    id = serializers.CharField(read_only=True)

    class Meta:
        model = Bill
        fields = [
            'id', 'table_number', 'is_takeaway', 'invoice_number',
            'order_type', 'amount', 'active', 'customer_name', 'contact',
            'payment_status',
        ]


class BillSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)

    class Meta:
        model = Bill
        exclude = ("updated_by",)


class DishSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    course = CourseSerializer(read_only=True)

    class Meta:
        model = Dish
        exclude = ("restaurant", "updated_by", "is_deleted")


class OrderSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    dish = DishSerializer(read_only=True)

    class Meta:
        model = Order
        exclude = ("restaurant", "bill", "updated_by", "created_at", "updated_at")


class KOTSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    status = KOTStatusField()
    bill = BillMinimalSerializer(read_only=True)

    class Meta:
        model = KOT
        exclude = ("restaurant",)
