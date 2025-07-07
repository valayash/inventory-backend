from rest_framework import serializers
from .models import InventoryItem, ShopInventory, ShopFinancialSummary, InventoryTransaction
from products.models import Frame


class InventoryItemSerializer(serializers.ModelSerializer):
    """Legacy serializer for backward compatibility"""
    class Meta:
        model = InventoryItem
        fields = '__all__'
        depth = 1


class ShopInventorySerializer(serializers.ModelSerializer):
    """Serializer for quantity-based inventory"""
    quantity_remaining = serializers.ReadOnlyField()
    total_cost = serializers.ReadOnlyField()
    total_revenue = serializers.ReadOnlyField()
    total_profit = serializers.ReadOnlyField()
    frame_name = serializers.CharField(source='frame.name', read_only=True)
    frame_product_id = serializers.CharField(source='frame.product_id', read_only=True)
    frame_price = serializers.DecimalField(source='frame.price', max_digits=10, decimal_places=2, read_only=True)
    frame_brand = serializers.CharField(source='frame.brand', read_only=True)
    
    class Meta:
        model = ShopInventory
        fields = [
            'id', 'shop', 'frame', 'quantity_received', 'quantity_sold', 
            'cost_per_unit', 'last_restocked', 'created_at',
            'quantity_remaining', 'total_cost', 'total_revenue', 'total_profit',
            'frame_name', 'frame_product_id', 'frame_price', 'frame_brand'
        ]
        read_only_fields = ['shop', 'created_at', 'last_restocked']


class ShopInventoryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating shop inventory"""
    frame_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = ShopInventory
        fields = ['frame_id', 'quantity_received', 'cost_per_unit']
    
    def create(self, validated_data):
        frame_id = validated_data.pop('frame_id')
        try:
            frame = Frame.objects.get(id=frame_id)
        except Frame.DoesNotExist:
            raise serializers.ValidationError({'frame_id': 'Frame does not exist'})
        
        validated_data['frame'] = frame
        return super().create(validated_data)


class ShopInventoryUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating shop inventory quantities"""
    quantity_to_add = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = ShopInventory
        fields = ['quantity_to_add', 'cost_per_unit']
    
    def update(self, instance, validated_data):
        quantity_to_add = validated_data.pop('quantity_to_add', 0)
        
        if quantity_to_add > 0:
            instance.quantity_received += quantity_to_add
        
        return super().update(instance, validated_data)


class ShopFinancialSummarySerializer(serializers.ModelSerializer):
    """Serializer for financial summary"""
    shop_name = serializers.CharField(source='shop.name', read_only=True)
    month_display = serializers.SerializerMethodField()
    
    class Meta:
        model = ShopFinancialSummary
        fields = [
            'id', 'shop', 'month', 'total_revenue', 'total_cost', 
            'total_profit', 'amount_to_pay_distributor', 'units_sold',
            'created_at', 'updated_at', 'shop_name', 'month_display'
        ]
        read_only_fields = ['shop', 'created_at', 'updated_at']
    
    def get_month_display(self, obj):
        return obj.month.strftime('%B %Y')


class InventoryTransactionSerializer(serializers.ModelSerializer):
    """Serializer for inventory transactions"""
    shop_name = serializers.CharField(source='shop_inventory.shop.name', read_only=True)
    frame_name = serializers.CharField(source='shop_inventory.frame.name', read_only=True)
    frame_product_id = serializers.CharField(source='shop_inventory.frame.product_id', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = InventoryTransaction
        fields = [
            'id', 'shop_inventory', 'transaction_type', 'quantity', 
            'unit_cost', 'unit_price', 'notes', 'created_at', 'created_by',
            'shop_name', 'frame_name', 'frame_product_id', 'created_by_username'
        ]
        read_only_fields = ['created_at', 'created_by']


class InventoryStockInSerializer(serializers.Serializer):
    """Serializer for bulk stock in operations"""
    shop_id = serializers.IntegerField()
    items = serializers.ListField(child=serializers.DictField())
    
    def validate_items(self, value):
        """Validate items structure"""
        for item in value:
            if not all(k in item for k in ['frame_id', 'quantity', 'cost_per_unit']):
                raise serializers.ValidationError(
                    "Each item must have 'frame_id', 'quantity', and 'cost_per_unit'"
                )
            if item['quantity'] <= 0:
                raise serializers.ValidationError("Quantity must be positive")
            if item['cost_per_unit'] <= 0:
                raise serializers.ValidationError("Cost per unit must be positive")
        return value


class InventorySaleSerializer(serializers.Serializer):
    """Serializer for processing sales"""
    shop_inventory_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    sale_price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    
    def validate(self, data):
        """Validate sale data"""
        try:
            shop_inventory = ShopInventory.objects.get(id=data['shop_inventory_id'])
        except ShopInventory.DoesNotExist:
            raise serializers.ValidationError({'shop_inventory_id': 'Shop inventory does not exist'})
        
        if shop_inventory.quantity_remaining < data['quantity']:
            raise serializers.ValidationError({
                'quantity': f'Not enough stock. Available: {shop_inventory.quantity_remaining}'
            })
        
        data['shop_inventory'] = shop_inventory
        return data


class ShopInventoryDashboardSerializer(serializers.ModelSerializer):
    """Serializer for dashboard view with summary data"""
    quantity_remaining = serializers.ReadOnlyField()
    total_value = serializers.SerializerMethodField()
    reorder_needed = serializers.SerializerMethodField()
    frame_name = serializers.CharField(source='frame.name', read_only=True)
    frame_product_id = serializers.CharField(source='frame.product_id', read_only=True)
    frame_price = serializers.DecimalField(source='frame.price', max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = ShopInventory
        fields = [
            'id', 'frame_name', 'frame_product_id', 'frame_price',
            'quantity_received', 'quantity_sold', 'quantity_remaining',
            'total_value', 'reorder_needed', 'last_restocked'
        ]
    
    def get_total_value(self, obj):
        """Calculate total value of remaining inventory"""
        return obj.quantity_remaining * obj.frame.price
    
    def get_reorder_needed(self, obj):
        """Simple reorder logic - reorder if less than 5 units"""
        return obj.quantity_remaining < 5 