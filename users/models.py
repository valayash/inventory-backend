from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        DISTRIBUTOR = 'DISTRIBUTOR', 'Distributor'
        SHOP_OWNER = 'SHOP_OWNER', 'Shop Owner'
    
    role = models.CharField(max_length=20, choices=Role.choices)
    shop = models.ForeignKey('shops.Shop', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
