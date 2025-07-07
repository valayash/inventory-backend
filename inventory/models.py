from django.db import models
from django.utils import timezone
from datetime import datetime

# Create your models here.

class InventoryItem(models.Model):
    """
    DEPRECATED: Legacy individual item tracking
    This model is kept for backward compatibility
    """
    class Status(models.TextChoices):
        IN_STOCK = 'IN_STOCK', 'In Stock'
        SOLD = 'SOLD', 'Sold'
    
    frame = models.ForeignKey('products.Frame', on_delete=models.PROTECT)
    shop = models.ForeignKey('shops.Shop', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_STOCK)
    date_stocked = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.frame.name} at {self.shop.name} - {self.get_status_display()}"


class ShopInventory(models.Model):
    """
    New quantity-based inventory tracking for each shop
    """
    shop = models.ForeignKey('shops.Shop', on_delete=models.CASCADE)
    frame = models.ForeignKey('products.Frame', on_delete=models.PROTECT)
    quantity_received = models.PositiveIntegerField(default=0, help_text="Total quantity received from distributor")
    quantity_sold = models.PositiveIntegerField(default=0, help_text="Total quantity sold to customers")
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2, help_text="Cost per unit shop pays to distributor")
    last_restocked = models.DateTimeField(auto_now=True, help_text="Last time inventory was restocked")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['shop', 'frame']
        verbose_name = 'Shop Inventory'
        verbose_name_plural = 'Shop Inventories'

    @property
    def quantity_remaining(self):
        """Calculate remaining quantity"""
        return max(0, self.quantity_received - self.quantity_sold)
    
    @property
    def total_cost(self):
        """Total cost paid to distributor for all units"""
        return self.quantity_received * self.cost_per_unit
    
    @property
    def total_revenue(self):
        """Total revenue from sold units"""
        return self.quantity_sold * self.frame.price
    
    @property
    def total_profit(self):
        """Total profit (revenue - cost for sold units)"""
        return self.total_revenue - (self.quantity_sold * self.cost_per_unit)
    
    def __str__(self):
        return f"{self.shop.name} - {self.frame.name} ({self.quantity_remaining} remaining)"


class ShopFinancialSummary(models.Model):
    """
    Monthly financial summary for each shop
    """
    shop = models.ForeignKey('shops.Shop', on_delete=models.CASCADE)
    month = models.DateField(help_text="First day of the month (YYYY-MM-01)")
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Total revenue from sales")
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Total cost of goods sold")
    total_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Total profit (revenue - cost)")
    amount_to_pay_distributor = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Amount owed to distributor")
    units_sold = models.PositiveIntegerField(default=0, help_text="Total units sold this month")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['shop', 'month']
        verbose_name = 'Shop Financial Summary'
        verbose_name_plural = 'Shop Financial Summaries'
        ordering = ['-month', 'shop']

    def __str__(self):
        return f"{self.shop.name} - {self.month.strftime('%B %Y')}"
    
    @classmethod
    def get_or_create_current_month(cls, shop):
        """Get or create financial summary for current month"""
        current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0).date()
        summary, created = cls.objects.get_or_create(
            shop=shop,
            month=current_month,
            defaults={
                'total_revenue': 0,
                'total_cost': 0,
                'total_profit': 0,
                'amount_to_pay_distributor': 0,
                'units_sold': 0
            }
        )
        return summary
    
    def update_from_sale(self, sale_amount, cost_per_unit):
        """Update summary when a sale is made"""
        self.total_revenue += sale_amount
        self.total_cost += cost_per_unit
        self.total_profit += (sale_amount - cost_per_unit)
        self.amount_to_pay_distributor += cost_per_unit
        self.units_sold += 1
        self.save()


class InventoryTransaction(models.Model):
    """
    Track inventory movements (stock in/out)
    """
    class TransactionType(models.TextChoices):
        STOCK_IN = 'STOCK_IN', 'Stock In'
        SALE = 'SALE', 'Sale'
        ADJUSTMENT = 'ADJUSTMENT', 'Adjustment'
    
    shop_inventory = models.ForeignKey(ShopInventory, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    quantity = models.IntegerField(help_text="Positive for stock in, negative for stock out")
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('users.User', on_delete=models.PROTECT)

    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.shop_inventory.shop.name} - {self.get_transaction_type_display()} - {self.quantity} units"
