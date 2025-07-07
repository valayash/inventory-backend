from django.conf import settings
from django.db import models


class Sale(models.Model):
    inventory_item = models.OneToOneField('inventory.InventoryItem', on_delete=models.SET_NULL, null=True, blank=True)
    lens_type = models.ForeignKey('products.LensType', on_delete=models.PROTECT)
    shop = models.ForeignKey('shops.Shop', on_delete=models.SET_NULL, null=True, blank=True)
    sold_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    sale_date = models.DateTimeField(auto_now_add=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        shop_name = self.shop.name if self.shop else "Deleted Shop"
        if self.inventory_item:
            item_name = self.inventory_item.frame.name
        else:
            item_name = "Deleted Item"
        return f"Sale of {item_name} at {shop_name} on {self.sale_date.date()}"
