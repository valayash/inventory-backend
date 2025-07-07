from django.db import models
from django.utils import timezone

# Create your models here.

class Frame(models.Model):
    """
    Model representing eyeglass frames in the inventory
    """
    
    # Keep these as reference for the frontend filter choices
    MATERIAL_CHOICES = [
        ('acetate', 'Acetate'),
        ('aluminum', 'Aluminum'),
        ('bamboo', 'Bamboo'),
        ('chrome', 'Chrome'),
        ('metal', 'Metal'),
        ('steel', 'Steel'),
        ('titanium', 'Titanium'),
        ('wood', 'Wood'),
    ]
    
    # Frame type choices based on the image
    FRAME_TYPE_CHOICES = [
        ('aviator', 'Aviator'),
        ('cat_eye', 'Cat-Eye'),
        ('rectangle', 'Rectangle'),
        ('round', 'Round'),
        ('square', 'Square'),
    ]
    
    # Color choices (common frame colors)
    COLOR_CHOICES = [
        ('black', 'Black'),
        ('brown', 'Brown'),
        ('gold', 'Gold'),
        ('silver', 'Silver'),
        ('blue', 'Blue'),
        ('red', 'Red'),
        ('green', 'Green'),
        ('transparent', 'Transparent'),
        ('tortoise', 'Tortoise'),
        ('grey', 'Grey'),
    ]
    
    product_id = models.CharField(max_length=50, unique=True, help_text="Unique product identifier")
    name = models.CharField(max_length=200, help_text="Frame model name")
    
    # Changed from choices to regular CharField to allow new values
    frame_type = models.CharField(max_length=50, help_text="Type of frame (e.g., aviator, round, etc.)")
    color = models.CharField(max_length=50, help_text="Frame color")
    material = models.CharField(max_length=50, help_text="Frame material")
    
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Frame price")
    brand = models.CharField(max_length=100, help_text="Frame brand/manufacturer")
    
    def __str__(self):
        return f"{self.brand} {self.name} ({self.product_id})"
    
    class Meta:
        ordering = ['brand', 'name']
        verbose_name = "Frame"
        verbose_name_plural = "Frames"

    @classmethod
    def get_available_choices(cls):
        """
        Get available choices for filters, including both predefined and actual database values
        """
        # Get all unique values from the database
        frame_types = list(cls.objects.values_list('frame_type', flat=True).distinct().order_by('frame_type'))
        colors = list(cls.objects.values_list('color', flat=True).distinct().order_by('color'))
        materials = list(cls.objects.values_list('material', flat=True).distinct().order_by('material'))
        brands = list(cls.objects.values_list('brand', flat=True).distinct().order_by('brand'))
        
        return {
            'frame_types': frame_types,
            'colors': colors,
            'materials': materials,
            'brands': brands,
        }


class LensType(models.Model):
    """
    Model representing different types of lenses available
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    price_modifier = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']
