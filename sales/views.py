from django.shortcuts import render
from django.db import transaction
from rest_framework import viewsets, generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as filters
from django.db import models
from .models import Sale
from .serializers import SaleSerializer, CreateSaleSerializer
from inventory_system.permissions import IsDistributor, IsShopOwner
from inventory.models import InventoryItem
from products.models import LensType


class SaleFilter(filters.FilterSet):
    shop = filters.NumberFilter(field_name='shop__id')
    sale_date_start = filters.DateTimeFilter(field_name='sale_date', lookup_expr='gte')
    sale_date_end = filters.DateTimeFilter(field_name='sale_date', lookup_expr='lte')
    sale_date_range = filters.DateFromToRangeFilter(field_name='sale_date')

    class Meta:
        model = Sale
        fields = ['shop', 'sale_date_start', 'sale_date_end', 'sale_date_range']


class DistributorSalesView(viewsets.ReadOnlyModelViewSet):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated, IsDistributor]
    filter_backends = [DjangoFilterBackend]
    filterset_class = SaleFilter
    ordering = ['-sale_date']  # Most recent sales first


class RecordSaleView(generics.CreateAPIView):
    serializer_class = CreateSaleSerializer
    permission_classes = [IsAuthenticated, IsShopOwner]

    @transaction.atomic
    def perform_create(self, serializer):
        """
        Handle the core sales logic with proper validation.
        Wrapped in transaction.atomic for data integrity.
        """
        # a. Extract inventory_item_id and lens_type_id from validated_data
        inventory_item_id = serializer.validated_data.get('inventory_item_id')
        lens_type_id = serializer.validated_data.get('lens_type_id')
        
        # b. Fetch the actual InventoryItem and LensType objects using these IDs
        try:
            inventory_item = InventoryItem.objects.get(id=inventory_item_id)
        except InventoryItem.DoesNotExist:
            raise ValidationError({"inventory_item_id": "Invalid inventory item ID."})
        
        try:
            lens_type = LensType.objects.get(id=lens_type_id)
        except LensType.DoesNotExist:
            raise ValidationError({"lens_type_id": "Invalid lens type ID."})
        
        # c. Perform all necessary validations
        # Check if the item belongs to the user's shop
        if inventory_item.shop != self.request.user.shop:
            raise ValidationError({"inventory_item_id": "This inventory item does not belong to your shop."})
        
        # Check if the item is in stock
        if inventory_item.status != 'IN_STOCK':
            raise ValidationError({"inventory_item_id": "This inventory item is not in stock."})
        
        # d. Mark the InventoryItem status as 'SOLD' and save it
        inventory_item.status = 'SOLD'
        inventory_item.save()
        
        # e. Calculate the total_price
        total_price = inventory_item.frame.price + lens_type.price
        
        # f. Call serializer.save() and pass in the model objects and extra data
        serializer.save(
            inventory_item=inventory_item,
            lens_type=lens_type,
            shop=self.request.user.shop,
            sold_by=self.request.user,
            total_price=total_price
        )
