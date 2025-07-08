from django.contrib import admin
from .models import Shop

@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner_name', 'phone', 'email', 'created_at')
    search_fields = ('name', 'owner_name')
