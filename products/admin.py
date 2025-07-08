from django.contrib import admin
from .models import Frame, LensType

@admin.register(Frame)
class FrameAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_id', 'brand', 'frame_type', 'color', 'material', 'price')
    list_filter = ('brand', 'frame_type', 'material', 'color')
    search_fields = ('name', 'product_id', 'brand')

@admin.register(LensType)
class LensTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'price_modifier')
    search_fields = ('name',)
