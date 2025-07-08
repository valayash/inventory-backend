import csv
import io
from django.db import transaction
from rest_framework import status, viewsets, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser

from ..models import InventoryItem
from ..serializers import InventoryItemSerializer
from products.models import Frame
from shops.models import Shop
from inventory_system.permissions import IsDistributor, IsShopOwner


class InventoryStockView(APIView):
    """LEGACY: Keep for backward compatibility"""
    permission_classes = [IsAuthenticated, IsDistributor]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        shop_id = request.data.get('shop_id')
        file_obj = request.FILES.get('file')

        if not shop_id:
            return Response(
                {'error': 'shop_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if not file_obj:
            return Response(
                {'error': 'file is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            shop = Shop.objects.get(id=shop_id)
        except Shop.DoesNotExist:
            return Response(
                {'error': 'Shop not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if file is CSV
        if not file_obj.name.endswith('.csv'):
            return Response(
                {'error': 'File must be a CSV'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                # Read CSV file
                file_data = file_obj.read().decode('utf-8')
                csv_reader = csv.DictReader(io.StringIO(file_data))
                
                created_items = []
                
                for row in csv_reader:
                    product_id = row.get('product_id')
                    name = row.get('name')
                    price = row.get('price')
                    
                    if not all([product_id, name, price]):
                        return Response(
                            {'error': 'CSV must contain product_id, name, and price columns'}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    # Create or update Frame
                    frame, created = Frame.objects.update_or_create(
                        product_id=product_id,
                        defaults={
                            'name': name,
                            'price': float(price)
                        }
                    )
                    
                    # Create InventoryItem
                    inventory_item = InventoryItem.objects.create(
                        frame=frame,
                        shop=shop
                    )
                    
                    created_items.append({
                        'inventory_item_id': inventory_item.id,
                        'frame_id': frame.id,
                        'product_id': product_id,
                        'frame_created': created
                    })
                
                return Response({
                    'message': f'Successfully processed {len(created_items)} items',
                    'created_items': created_items
                }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response(
                {'error': f'Error processing file: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Legacy view for backward compatibility
class ShopInventoryLegacyViewSet(viewsets.ReadOnlyModelViewSet):
    """Legacy ViewSet for old inventory system"""
    serializer_class = InventoryItemSerializer
    permission_classes = [IsAuthenticated, IsShopOwner]
    filter_backends = [filters.SearchFilter]
    search_fields = ['frame__name', 'frame__product_id']

    def get_queryset(self):
        """Return only IN_STOCK inventory items for the user's shop."""
        return InventoryItem.objects.filter(
            status='IN_STOCK',
            shop=self.request.user.shop
        )
