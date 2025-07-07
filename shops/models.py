from django.db import models

# Create your models here.

class Shop(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    owner_name = models.CharField(max_length=200, blank=True, default="", help_text="Shop owner's full name")
    phone = models.CharField(max_length=20, blank=True, default="", help_text="Shop contact phone")
    email = models.EmailField(blank=True, default="", help_text="Shop contact email")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
