from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Shop
from .serializers import ShopSerializer, CreateShopSerializer, ShopListSerializer
from inventory_system.permissions import IsDistributor

# Create your views here.

class ShopViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing shops - only distributors can create/manage shops
    """
    queryset = Shop.objects.all()
    permission_classes = [IsAuthenticated, IsDistributor]
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action
        """
        if self.action == 'create':
            return CreateShopSerializer
        elif self.action == 'list':
            return ShopListSerializer
        return ShopSerializer
    
    def create(self, request, *args, **kwargs):
        """
        Create a new shop along with its owner user account
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            shop = serializer.save()
            # Return shop details with success message
            response_serializer = ShopListSerializer(shop)
            return Response({
                'message': 'Shop and user account created successfully',
                'shop': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
