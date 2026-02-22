from django.shortcuts import render
from common.decorators import owner_required, manager_or_above_required
from core.models.table import Table


@manager_or_above_required
def settings(request):
    restaurant = request.restaurant
    message = None
    message_type = None
    if request.method == "POST":
        try:
            restaurant.name = request.POST.get("name", restaurant.name)
            restaurant.display_name = request.POST.get(
                "display_name", restaurant.display_name
            )
            restaurant.contact = request.POST.get("contact", restaurant.contact)
            restaurant.street_address = request.POST.get(
                "street_address", restaurant.street_address
            )
            restaurant.locality = request.POST.get("locality", restaurant.locality)
            restaurant.city = request.POST.get("city", restaurant.city)
            restaurant.district = request.POST.get("district", restaurant.district)
            restaurant.state = request.POST.get("state", restaurant.state)
            restaurant.country = request.POST.get("country", restaurant.country)
            restaurant.pincode = request.POST.get("pincode", restaurant.pincode)
            restaurant.gstin = request.POST.get("gstin", restaurant.gstin)
            restaurant.upi_id = request.POST.get("upi_id", restaurant.upi_id)
            restaurant.save()
            message = "Settings updated successfully."
            message_type = "success"
        except Exception as e:
            message = f"Error updating settings: {str(e)}"
            message_type = "error"
        return render(
            request,
            "settings.html",
            {
                "restaurant": restaurant,
                "message": message,
                "message_type": message_type,
                "tables": Table.get_tables_for_restaurant(restaurant),
            },
        )

    return render(
        request,
        "settings.html",
        {
            "restaurant": restaurant,
            "tables": Table.get_tables_for_restaurant(restaurant),
        },
    )


@owner_required
def team_page(request):
    return render(request, "team.html")
