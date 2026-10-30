from rest_framework.permissions import BasePermission

from .roles import UserRole, get_user_role


class HasFarmerDataAccess(BasePermission):
    message = "Link your account to a farmer profile or contact an administrator."

    def has_permission(self, request, view):
        return get_user_role(request.user) != UserRole.UNLINKED


class IsAdministrator(BasePermission):
    message = "Only administrators can manage staff privileges."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)