from django.db.models import F
from rest_framework import viewsets, filters, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters

from ..models import (
    ShopInventory, ShopFinancialSummary, InventoryTransaction
)
from ..serializers import (
    ShopInventorySerializer, ShopInventoryCreateSerializer,
    ShopInventoryUpdateSerializer, ShopFinancialSummarySerializer,
    InventoryTransactionSerializer, ShopInventoryDashboardSerializer
)


class ShopInventoryFilter(django_filters.FilterSet):
    """Filter for shop inventory"""
    frame_name = django_filters.CharFilter(field_name='frame__name', lookup_expr='icontains')
    frame_product_id = django_filters.CharFilter(field_name='frame__product_id', lookup_expr='icontains')
    frame_brand = django_filters.CharFilter(field_name='frame__brand', lookup_expr='icontains')
    low_stock = django_filters.BooleanFilter(method='filter_low_stock')
    
    class Meta:
        model = ShopInventory
        fields = ['frame_name', 'frame_product_id', 'frame_brand', 'low_stock']
    
    def filter_low_stock(self, queryset, name, value):
        if value:
            return queryset.filter(quantity_received__lt=F('quantity_sold') + 5)
        return queryset


class ShopInventoryViewSet(viewsets.ModelViewSet):
    """ViewSet for shop inventory management"""
    serializer_class = ShopInventorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ShopInventoryFilter
    search_fields = ['frame__name', 'frame__product_id', 'frame__brand']
    ordering_fields = ['quantity_remaining', 'last_restocked', 'frame__name']
    ordering = ['-last_restocked']

    def get_queryset(self):
        """Return inventory for the appropriate shop"""
        user = self.request.user
        if hasattr(user, 'role') and user.role == 'SHOP_OWNER':
            return ShopInventory.objects.filter(shop=user.shop)
        elif hasattr(user, 'role') and user.role == 'DISTRIBUTOR':
            # Distributors can see all shop inventories
            return ShopInventory.objects.all()
        return ShopInventory.objects.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return ShopInventoryCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ShopInventoryUpdateSerializer
        elif self.action == 'dashboard':
            return ShopInventoryDashboardSerializer
        return ShopInventorySerializer

    def perform_create(self, serializer):
        """Set the shop for new inventory items"""
        if hasattr(self.request.user, 'shop') and self.request.user.shop:
            serializer.save(shop=self.request.user.shop)
        else:
            raise serializers.ValidationError("User must be associated with a shop")

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get dashboard view with summary data"""
        queryset = self.get_queryset()
        serializer = ShopInventoryDashboardSerializer(queryset, many=True)
        
        # Calculate summary statistics
        total_items = queryset.count()
        total_value = sum(item.quantity_remaining * item.frame.price for item in queryset)
        low_stock_count = queryset.filter(quantity_received__lt=F('quantity_sold') + 5).count()
        
        return Response({
            'inventory': serializer.data,
            'summary': {
                'total_items': total_items,
                'total_value': total_value,
                'low_stock_count': low_stock_count
            }
        })

    @action(detail=True, methods=['post'])
    def add_stock(self, request, pk=None):
        """Add stock to existing inventory"""
        inventory = self.get_object()
        quantity = request.data.get('quantity', 0)
        cost_per_unit = request.data.get('cost_per_unit')
        
        if quantity <= 0:
            return Response(
                {'error': 'Quantity must be positive'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            inventory.quantity_received += quantity
            if cost_per_unit:
                inventory.cost_per_unit = cost_per_unit
            inventory.save()
            
            # Create transaction record
            InventoryTransaction.objects.create(
                shop_inventory=inventory,
                transaction_type='STOCK_IN',
                quantity=quantity,
                unit_cost=cost_per_unit or inventory.cost_per_unit,
                created_by=request.user,
                notes=f"Stock added via API"
            )
        
        return Response({
            'message': f'Added {quantity} units successfully',
            'new_quantity': inventory.quantity_received
        })


class ShopFinancialSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for financial summaries"""
    serializer_class = ShopFinancialSummarySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['month']
    ordering = ['-month']

    def get_queryset(self):
        """Return financial summaries for the appropriate shop"""
        user = self.request.user
        if hasattr(user, 'role') and user.role == 'SHOP_OWNER':
            return ShopFinancialSummary.objects.filter(shop=user.shop)
        elif hasattr(user, 'role') and user.role == 'DISTRIBUTOR':
            return ShopFinancialSummary.objects.all()
        return ShopFinancialSummary.objects.none()


class InventoryTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for inventory transactions"""
    serializer_class = InventoryTransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['transaction_type', 'shop_inventory__shop']
    ordering = ['-created_at']

    def get_queryset(self):
        """Return transactions for the appropriate shop"""
        user = self.request.user
        if hasattr(user, 'role') and user.role == 'SHOP_OWNER':
            return InventoryTransaction.objects.filter(shop_inventory__shop=user.shop)
        elif hasattr(user, 'role') and user.role == 'DISTRIBUTOR':
            return InventoryTransaction.objects.all()
        return InventoryTransaction.objects.none()
