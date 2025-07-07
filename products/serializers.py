from rest_framework import serializers
from .models import Frame, LensType


class FrameSerializer(serializers.ModelSerializer):
    frame_id = serializers.CharField(source='product_id')
    frame_name = serializers.CharField(source='name')
    
    class Meta:
        model = Frame
        fields = ['frame_id', 'frame_name', 'frame_type', 'price', 'color', 'material', 'brand']


class LensTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LensType
        fields = '__all__' 