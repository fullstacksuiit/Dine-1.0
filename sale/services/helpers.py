# Helper Functions
from django.shortcuts import get_object_or_404

def handle_get_object_or_404(model, lookup_field, lookup_value):
    """
    Helper to fetch an object or return 404.

    Args:
        model: Django model class to query
        lookup_field: Field name to filter on (e.g. "id")
        lookup_value: Value to search for, which could be a UUID string

    Returns:
        Object instance if found, None if value is None or invalid format
    """
    if lookup_value is None:
        return None

    try:
        # For UUID fields, explicitly handle string representation
        if lookup_field == "id" and hasattr(model, "id") and isinstance(lookup_value, str):
            import uuid
            try:
                # Try to convert the string to a UUID
                lookup_value = uuid.UUID(lookup_value)
            except (ValueError, TypeError, AttributeError):
                # If it's not a valid UUID string, let it pass through
                # (the database query will fail appropriately)
                pass

        return get_object_or_404(model, **{lookup_field: lookup_value})
    except (ValueError, TypeError):
        # Handle case where lookup_value is not in correct format (e.g., invalid UUID)
        return None

def handle_serializer_validation(serializer_class, data, instance=None):
    """Helper to validate and save serializer data."""
    serializer = serializer_class(instance, data=data) if instance else serializer_class(data=data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return serializer