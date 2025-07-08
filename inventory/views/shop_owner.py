from django.db import transaction
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from ..models import (
    ShopFinancialSummary, InventoryTransaction
)
from ..serializers import (
    InventorySaleSerializer
)
from inventory_system.permissions import IsShopOwner


class InventorySaleView(APIView):
    """Process sales and update inventory"""
    permission_classes = [IsAuthenticated, IsShopOwner]
    
    def post(self, request):
        serializer = InventorySaleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        shop_inventory = serializer.validated_data['shop_inventory']
        quantity = serializer.validated_data['quantity']
        sale_price = serializer.validated_data['sale_price']
        
        # Verify shop ownership
        if shop_inventory.shop != request.user.shop:
            return Response(
                {'error': 'This inventory item does not belong to your shop'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        with transaction.atomic():
            # Update inventory
            shop_inventory.quantity_sold += quantity
            shop_inventory.save()
            
            # Create transaction record
            InventoryTransaction.objects.create(
                shop_inventory=shop_inventory,
                transaction_type='SALE',
                quantity=-quantity,  # Negative for stock out
                unit_price=sale_price,
                unit_cost=shop_inventory.cost_per_unit,
                created_by=request.user,
                notes=f"Sale processed"
            )
            
            # Update financial summary
            total_sale_amount = quantity * sale_price
            total_cost = quantity * shop_inventory.cost_per_unit
            
            financial_summary = ShopFinancialSummary.get_or_create_current_month(shop_inventory.shop)
            financial_summary.total_revenue += total_sale_amount
            financial_summary.total_cost += total_cost
            financial_summary.total_profit += (total_sale_amount - total_cost)
            financial_summary.amount_to_pay_distributor += total_cost
            financial_summary.units_sold += quantity
            financial_summary.save()
        
        return Response({
            'message': f'Sale processed successfully',
            'quantity_sold': quantity,
            'total_amount': total_sale_amount,
            'remaining_stock': shop_inventory.quantity_remaining
        })
