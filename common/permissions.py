from rest_framework import permissions

class IsOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.staff and request.staff.is_owner


class IsOwnerOrManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.staff and (request.staff.is_manager or request.staff.is_owner)
