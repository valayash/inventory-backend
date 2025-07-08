from django.contrib import admin
from .models import ShopInventory, ShopFinancialSummary, InventoryTransaction

@admin.register(ShopInventory)
class ShopInventoryAdmin(admin.ModelAdmin):
    list_display = ('shop', 'frame', 'quantity_received', 'quantity_sold', 'quantity_remaining', 'cost_per_unit', 'last_restocked')
    list_filter = ('shop', 'frame__brand')
    search_fields = ('shop__name', 'frame__name', 'frame__product_id')
    readonly_fields = ('quantity_remaining',)

    def quantity_remaining(self, obj):
        return obj.quantity_remaining
    quantity_remaining.short_description = 'Remaining'

@admin.register(ShopFinancialSummary)
class ShopFinancialSummaryAdmin(admin.ModelAdmin):
    list_display = ('shop', 'month', 'total_revenue', 'total_cost', 'total_profit', 'amount_to_pay_distributor', 'units_sold')
    list_filter = ('shop', 'month')
    search_fields = ('shop__name',)

@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ('shop_inventory', 'transaction_type', 'quantity', 'unit_cost', 'unit_price', 'created_at', 'created_by')
    list_filter = ('transaction_type', 'shop_inventory__shop')
    search_fields = ('shop_inventory__shop__name', 'shop_inventory__frame__name')
