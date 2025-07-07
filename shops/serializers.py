from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import Shop

User = get_user_model()


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = '__all__'


class CreateShopSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a shop along with its owner user account
    """
    # User account fields
    username = serializers.CharField(max_length=150, help_text="Username for shop owner login")
    password = serializers.CharField(write_only=True, min_length=6, help_text="Password for shop owner")
    confirm_password = serializers.CharField(write_only=True, help_text="Confirm password")
    
    class Meta:
        model = Shop
        fields = ['name', 'address', 'owner_name', 'phone', 'email', 'username', 'password', 'confirm_password']
    
    def validate_username(self, value):
        """
        Check that username is not already taken
        """
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value
    
    def validate_email(self, value):
        """
        Check that email is not already used by another shop
        """
        if Shop.objects.filter(email=value).exists():
            raise serializers.ValidationError("A shop with this email already exists.")
        return value
    
    def validate(self, attrs):
        """
        Check that passwords match
        """
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        return attrs
    
    @transaction.atomic
    def create(self, validated_data):
        """
        Create shop and associated user account
        """
        # Extract user data
        username = validated_data.pop('username')
        password = validated_data.pop('password')
        validated_data.pop('confirm_password')  # Remove confirm_password as it's not needed
        
        # Create the shop
        shop = Shop.objects.create(**validated_data)
        
        # Create the user account
        user = User.objects.create_user(
            username=username,
            password=password,
            email=validated_data['email'],
            role='SHOP_OWNER',
            shop=shop
        )
        
        return shop


class ShopListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing shops with basic info
    """
    user_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Shop
        fields = ['id', 'name', 'address', 'owner_name', 'phone', 'email', 'created_at', 'user_count']
    
    def get_user_count(self, obj):
        """
        Get number of users associated with this shop
        """
        return obj.user_set.count() 