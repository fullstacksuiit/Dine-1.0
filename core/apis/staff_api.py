from django.contrib.auth.models import User, Group
from django.http import JsonResponse, HttpResponseNotAllowed
from core.models.staff import Role, Staff
from core.models.restaurant import Restaurant
from core.models.table import Table
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from common.permissions import IsOwner


class TeamListCreateAPI(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get(self, request):
        staff_qs = Staff.get_staff_by_restaurant(request.restaurant)
        data = [
            {
                "id": s.id,
                "username": s.user.username,
                "role": (
                    "OWNER" if s.is_owner else "MANAGER" if s.is_manager else "WAITER"
                ),
                "contact": s.phone_number,
                "active": s.is_active,
            }
            for s in staff_qs
        ]
        return Response(data)

    def post(self, request):
        payload = request.data
        password = payload.get("password")
        username = payload.get("username", "")
        if not username or not password:
            return Response(
                {"error": "Username and password required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if User.objects.filter(username=username).exists():
            return Response(
                {"error": "Username already exists. Please choose another one"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = User(username=username)
        user.set_password(password)
        user.save()
        staff = Staff.objects.create(
            restaurant=request.restaurant,
            user=user,
            phone_number=payload.get("contact", ""),
        )
        role = payload.get("role")
        group, _ = Group.objects.get_or_create(name=role.upper() or Role.WAITER.value)
        user.groups.add(group)
        return Response({"id": staff.id}, status=status.HTTP_201_CREATED)


class TeamDetailAPI(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_object(self, request, pk):
        return get_object_or_404(Staff, id=pk, restaurant=request.restaurant)

    def get(self, request, pk):
        staff = self.get_object(request, pk)
        data = {
            "id": staff.id,
            "username": staff.user.username,
            "role": (
                "OWNER"
                if staff.is_owner
                else "MANAGER" if staff.is_manager else "WAITER"
            ),
            "contact": staff.phone_number,
            "active": staff.is_active,
        }
        return Response(data)

    def put(self, request, pk):
        staff = self.get_object(request, pk)
        payload = request.data
        user = staff.user
        if payload.get("username"):
            user.username = payload["username"]
        if payload.get("password"):
            user.set_password(payload["password"])
        user.save()
        staff.phone_number = payload.get("contact", staff.phone_number)
        if payload.get("role"):
            user.groups.clear()
            group, _ = Group.objects.get_or_create(name=payload["role"])
            user.groups.add(group)
        staff.save()
        return Response({"success": True})

    def delete(self, request, pk):
        staff = self.get_object(request, pk)
        staff.soft_delete()
        return Response({"success": True})


class CurrentUserAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get details of the currently authenticated user"""
        staff = request.staff
        if not staff:
            # If user doesn't have a staff record, return basic user info
            return Response(status=status.HTTP_404_NOT_FOUND)

        user = staff.user
        data = {
            "id": staff.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": (
                "OWNER" if staff.is_owner else "MANAGER" if staff.is_manager else "WAITER"
            ),
            "contact": staff.phone_number,
            "active": staff.is_active,
            "restaurant": {
                "id": staff.restaurant.id,
                "name": staff.restaurant.display_name,
                "contact": staff.restaurant.contact,
                "street_address": staff.restaurant.street_address,
                "locality": staff.restaurant.locality,
                "city": staff.restaurant.city,
                "district": staff.restaurant.district,
                "state": staff.restaurant.state,
                "country": staff.restaurant.country,
                "pincode": staff.restaurant.pincode,
                "gstin": staff.restaurant.gstin,
                "upi_id": staff.restaurant.upi_id,
                "full_address": staff.restaurant.full_address,
                "num_tables": staff.restaurant.num_tables,
                "tables": [
                    {"id": str(t.id), "name": t.name, "display_order": t.display_order}
                    for t in Table.get_tables_for_restaurant(staff.restaurant)
                ],
            } if staff.restaurant else None,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "date_joined": user.date_joined.isoformat(),
            "last_login": user.last_login.isoformat() if user.last_login else None,
        }

        return Response(data)


class RestaurantSettingsAPI(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get(self, request):
        """Get restaurant settings"""
        restaurant = request.restaurant
        if not restaurant:
            return Response(
                {"error": "No restaurant found for this user"},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = {
            "id": restaurant.id,
            "name": restaurant.display_name,
            "contact": restaurant.contact,
            "street_address": restaurant.street_address,
            "locality": restaurant.locality,
            "city": restaurant.city,
            "district": restaurant.district,
            "state": restaurant.state,
            "country": restaurant.country,
            "pincode": restaurant.pincode,
            "gstin": restaurant.gstin,
            "upi_id": restaurant.upi_id,
            "full_address": restaurant.full_address,
            "num_tables": restaurant.num_tables,
            "tables": [
                {"id": str(t.id), "name": t.name, "display_order": t.display_order}
                for t in Table.get_tables_for_restaurant(restaurant)
            ],
        }
        return Response(data)

    def put(self, request):
        """Update restaurant settings"""
        restaurant = request.restaurant
        if not restaurant:
            return Response(
                {"error": "No restaurant found for this user"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Update restaurant fields - allow empty strings to clear fields
        payload = request.data

        # Validate required fields
        if "name" in payload and not payload["name"].strip():
            return Response(
                {"error": "Restaurant name cannot be empty"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if "name" in payload:
            restaurant.display_name = payload["name"].strip()
        if "contact" in payload:
            restaurant.contact = payload["contact"].strip()
        if "street_address" in payload:
            restaurant.street_address = payload["street_address"].strip()
        if "locality" in payload:
            restaurant.locality = payload["locality"].strip()
        if "city" in payload:
            restaurant.city = payload["city"].strip()
        if "district" in payload:
            restaurant.district = payload["district"].strip()
        if "state" in payload:
            restaurant.state = payload["state"].strip()
        if "country" in payload:
            restaurant.country = payload["country"].strip()
        if "pincode" in payload:
            restaurant.pincode = payload["pincode"].strip()
        if "gstin" in payload:
            restaurant.gstin = payload["gstin"].strip()
        if "upi_id" in payload:
            restaurant.upi_id = payload["upi_id"].strip()
        if "num_tables" in payload:
            try:
                val = int(payload["num_tables"])
                if 1 <= val <= 200:
                    restaurant.num_tables = val
            except (ValueError, TypeError):
                pass

        try:
            restaurant.save()
            return Response({"success": True, "message": "Restaurant settings updated successfully"})
        except Exception as e:
            return Response(
                {"error": f"Failed to save restaurant settings: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
