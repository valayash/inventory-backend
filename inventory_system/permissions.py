from rest_framework.permissions import BasePermission


class IsDistributor(BasePermission):
    """
    Custom permission to only allow authenticated users with 'DISTRIBUTOR' role.
    Works with JWT authentication middleware that populates request.user.
    """
    
    def has_permission(self, request, view):
        # Check if user exists and is authenticated (populated by JWT middleware)
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user has the required role
        return hasattr(request.user, 'role') and request.user.role == 'DISTRIBUTOR'


class IsShopOwner(BasePermission):
    """
    Custom permission to only allow authenticated users with 'SHOP_OWNER' role.
    Works with JWT authentication middleware that populates request.user.
    """
    
    def has_permission(self, request, view):
        # Check if user exists and is authenticated (populated by JWT middleware)
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user has the required role
        return hasattr(request.user, 'role') and request.user.role == 'SHOP_OWNER' 