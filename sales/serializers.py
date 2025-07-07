from rest_framework import serializers
from .models import Sale


class SaleSerializer(serializers.ModelSerializer):
    inventory_item_name = serializers.SerializerMethodField()
    shop_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Sale
        fields = '__all__'
        depth = 1
    
    def get_inventory_item_name(self, obj):
        """Get the inventory item name, handling null values"""
        if obj.inventory_item and obj.inventory_item.frame:
            return obj.inventory_item.frame.name
        return "Deleted Item"
    
    def get_shop_name(self, obj):
        """Get the shop name, handling null values"""
        if obj.shop:
            return obj.shop.name
        return "Deleted Shop"


class CreateSaleSerializer(serializers.ModelSerializer):
    inventory_item_id = serializers.IntegerField(write_only=True)
    lens_type_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Sale
        fields = ['inventory_item_id', 'lens_type_id'] 