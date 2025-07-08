import csv
import io
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser

from ..models import (
    ShopInventory, ShopFinancialSummary, InventoryTransaction
)
from ..serializers import (
    ShopInventorySerializer, InventoryStockInSerializer
)
from products.models import Frame
from shops.models import Shop
from inventory_system.permissions import IsDistributor


# Inventory Distribution Views for Distributors

class InventoryDistributionView(APIView):
    """Main view for distributor inventory distribution management"""
    permission_classes = [IsAuthenticated, IsDistributor]
    
    def get(self, request):
        """Get distribution dashboard with shops, frames, and current inventory"""
        
        # Get all shops
        shops = Shop.objects.all().values('id', 'name', 'address', 'owner_name')
        
        # Get all frames
        frames = Frame.objects.all().values(
            'id', 'product_id', 'name', 'price', 'brand', 'frame_type', 'color', 'material'
        )
        
        # Get current inventory summary by shop
        shop_inventory_summary = []
        for shop in shops:
            shop_data = dict(shop)
            inventories = ShopInventory.objects.filter(shop_id=shop['id'])
            
            total_items = inventories.count()
            total_value = sum(inv.quantity_remaining * inv.frame.price for inv in inventories)
            low_stock_count = inventories.filter(
                quantity_received__lt=F('quantity_sold') + 5
            ).count()
            
            shop_data.update({
                'total_items': total_items,
                'total_value': float(total_value),
                'low_stock_count': low_stock_count,
                'last_distribution': inventories.order_by('-last_restocked').first().last_restocked if inventories.exists() else None
            })
            shop_inventory_summary.append(shop_data)
        
        # Get recent distributions
        recent_transactions = InventoryTransaction.objects.filter(
            transaction_type='STOCK_IN'
        ).select_related(
            'shop_inventory__shop', 'shop_inventory__frame', 'created_by'
        ).order_by('-created_at')[:10]
        
        recent_distributions = []
        for transaction in recent_transactions:
            recent_distributions.append({
                'id': transaction.id,
                'shop_name': transaction.shop_inventory.shop.name,
                'frame_name': transaction.shop_inventory.frame.name,
                'product_id': transaction.shop_inventory.frame.product_id,
                'quantity': transaction.quantity,
                'unit_cost': float(transaction.unit_cost) if transaction.unit_cost else None,
                'created_at': transaction.created_at,
                'created_by': transaction.created_by.username
            })
        
        return Response({
            'shops': list(shops),
            'frames': list(frames),
            'shop_inventory_summary': shop_inventory_summary,
            'recent_distributions': recent_distributions
        })


class InventoryDistributionBulkView(APIView):
    """Bulk inventory distribution to multiple shops"""
    permission_classes = [IsAuthenticated, IsDistributor]
    
    def post(self, request):
        """
        Distribute inventory to multiple shops
        Expected format:
        {
            "distributions": [
                {
                    "shop_id": 1,
                    "items": [
                        {"frame_id": 1, "quantity": 10, "cost_per_unit": 30.00},
                        {"frame_id": 2, "quantity": 5, "cost_per_unit": 25.00}
                    ]
                },
                {
                    "shop_id": 2,
                    "items": [...]
                }
            ]
        }
        """
        
        distributions = request.data.get('distributions', [])
        
        if not distributions:
            return Response(
                {'error': 'No distributions provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        results = []
        total_items_distributed = 0
        
        with transaction.atomic():
            for distribution in distributions:
                shop_id = distribution.get('shop_id')
                items = distribution.get('items', [])
                
                if not shop_id or not items:
                    return Response(
                        {'error': 'Each distribution must have shop_id and items'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                try:
                    shop = Shop.objects.get(id=shop_id)
                except Shop.DoesNotExist:
                    return Response(
                        {'error': f'Shop with ID {shop_id} not found'}, 
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                shop_result = {
                    'shop_id': shop_id,
                    'shop_name': shop.name,
                    'items_processed': [],
                    'total_items': 0
                }
                
                for item_data in items:
                    frame_id = item_data.get('frame_id')
                    quantity = item_data.get('quantity', 0)
                    cost_per_unit = item_data.get('cost_per_unit', 0)
                    
                    if not all([frame_id, quantity > 0, cost_per_unit > 0]):
                        return Response(
                            {'error': 'Each item must have frame_id, quantity > 0, and cost_per_unit > 0'}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    try:
                        frame = Frame.objects.get(id=frame_id)
                    except Frame.DoesNotExist:
                        return Response(
                            {'error': f'Frame with ID {frame_id} not found'}, 
                            status=status.HTTP_404_NOT_FOUND
                        )
                    
                    # Get or create shop inventory
                    shop_inventory, created = ShopInventory.objects.get_or_create(
                        shop=shop,
                        frame=frame,
                        defaults={
                            'quantity_received': quantity,
                            'cost_per_unit': cost_per_unit
                        }
                    )
                    
                    if not created:
                        # Update existing inventory
                        shop_inventory.quantity_received += quantity
                        shop_inventory.cost_per_unit = cost_per_unit
                        shop_inventory.save()
                    
                    # Create transaction record
                    InventoryTransaction.objects.create(
                        shop_inventory=shop_inventory,
                        transaction_type='STOCK_IN',
                        quantity=quantity,
                        unit_cost=cost_per_unit,
                        created_by=request.user,
                        notes=f"Bulk distribution"
                    )
                    
                    shop_result['items_processed'].append({
                        'frame_id': frame_id,
                        'frame_name': frame.name,
                        'product_id': frame.product_id,
                        'quantity_distributed': quantity,
                        'cost_per_unit': float(cost_per_unit),
                        'new_total_quantity': shop_inventory.quantity_received,
                        'inventory_created': created
                    })
                    
                    shop_result['total_items'] += quantity
                    total_items_distributed += quantity
                
                results.append(shop_result)
        
        return Response({
            'message': f'Successfully distributed {total_items_distributed} items to {len(results)} shops',
            'total_items_distributed': total_items_distributed,
            'shops_updated': len(results),
            'results': results
        }, status=status.HTTP_201_CREATED)


class ShopInventoryByShopView(APIView):
    """Get detailed inventory for a specific shop (for distributors)"""
    permission_classes = [IsAuthenticated, IsDistributor]
    
    def get(self, request, shop_id):
        """Get detailed inventory for a specific shop"""
        try:
            shop = Shop.objects.get(id=shop_id)
        except Shop.DoesNotExist:
            return Response(
                {'error': 'Shop not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get shop inventory
        inventories = ShopInventory.objects.filter(shop=shop).select_related('frame')
        serializer = ShopInventorySerializer(inventories, many=True)
        
        # Calculate shop summary
        total_items = inventories.count()
        total_value = sum(inv.quantity_remaining * inv.frame.price for inv in inventories)
        total_cost = sum(inv.total_cost for inv in inventories)
        low_stock_items = inventories.filter(quantity_received__lt=F('quantity_sold') + 5)
        
        # Get financial summary for current month
        financial_summary = ShopFinancialSummary.get_or_create_current_month(shop)
        
        return Response({
            'shop': {
                'id': shop.id,
                'name': shop.name,
                'address': shop.address,
                'owner_name': shop.owner_name,
                'phone': shop.phone,
                'email': shop.email
            },
            'inventory': serializer.data,
            'summary': {
                'total_items': total_items,
                'total_value': float(total_value),
                'total_cost': float(total_cost),
                'low_stock_count': low_stock_items.count(),
                'low_stock_items': ShopInventorySerializer(low_stock_items, many=True).data
            },
            'financial_summary': {
                'month': financial_summary.month.strftime('%B %Y'),
                'total_profit': float(financial_summary.total_profit),
                'amount_to_pay_distributor': float(financial_summary.amount_to_pay_distributor),
                'units_sold': financial_summary.units_sold
            }
        })


class InventoryStockInView(APIView):
    """Bulk stock in operation for distributors"""
    permission_classes = [IsAuthenticated, IsDistributor]
    
    def post(self, request):
        serializer = InventoryStockInSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        shop_id = serializer.validated_data['shop_id']
        items = serializer.validated_data['items']
        
        try:
            shop = Shop.objects.get(id=shop_id)
        except Shop.DoesNotExist:
            return Response(
                {'error': 'Shop not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        with transaction.atomic():
            processed_items = []
            
            for item_data in items:
                try:
                    frame = Frame.objects.get(id=item_data['frame_id'])
                except Frame.DoesNotExist:
                    return Response(
                        {'error': f'Frame with ID {item_data["frame_id"]} not found'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Get or create shop inventory
                shop_inventory, created = ShopInventory.objects.get_or_create(
                    shop=shop,
                    frame=frame,
                    defaults={
                        'quantity_received': item_data['quantity'],
                        'cost_per_unit': item_data['cost_per_unit']
                    }
                )
                
                if not created:
                    # Update existing inventory
                    shop_inventory.quantity_received += item_data['quantity']
                    shop_inventory.cost_per_unit = item_data['cost_per_unit']
                    shop_inventory.save()
                
                # Create transaction record
                InventoryTransaction.objects.create(
                    shop_inventory=shop_inventory,
                    transaction_type='STOCK_IN',
                    quantity=item_data['quantity'],
                    unit_cost=item_data['cost_per_unit'],
                    created_by=request.user,
                    notes=f"Bulk stock in by distributor"
                )
                
                processed_items.append({
                    'frame_id': frame.id,
                    'frame_name': frame.name,
                    'product_id': frame.product_id,
                    'quantity_added': item_data['quantity'],
                    'new_total': shop_inventory.quantity_received,
                    'inventory_created': created
                })
        
        return Response({
            'message': f'Successfully processed {len(processed_items)} items for {shop.name}',
            'processed_items': processed_items
        }, status=status.HTTP_201_CREATED)


class InventoryCSVUploadView(APIView):
    """CSV upload endpoint for inventory management"""
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
                
                processed_items = []
                errors = []
                
                for row_num, row in enumerate(csv_reader, start=2):  # Start from 2 to account for header
                    frame_id = row.get('frame_id', '').strip()
                    quantity_str = row.get('quantity', '').strip()
                    
                    if not frame_id or not quantity_str:
                        errors.append(f"Row {row_num}: Missing frame_id or quantity")
                        continue
                    
                    try:
                        quantity = int(quantity_str)
                        if quantity <= 0:
                            errors.append(f"Row {row_num}: Quantity must be positive")
                            continue
                    except ValueError:
                        errors.append(f"Row {row_num}: Invalid quantity format")
                        continue
                    
                    # Find frame by product_id
                    try:
                        frame = Frame.objects.get(product_id=frame_id)
                    except Frame.DoesNotExist:
                        errors.append(f"Row {row_num}: Frame with ID '{frame_id}' not found")
                        continue
                    
                    # Get or create shop inventory
                    shop_inventory, created = ShopInventory.objects.get_or_create(
                        shop=shop,
                        frame=frame,
                        defaults={
                            'quantity_received': quantity,
                            'cost_per_unit': frame.price
                        }
                    )
                    
                    if not created:
                        # Update existing inventory
                        shop_inventory.quantity_received += quantity
                        shop_inventory.save()
                    
                    # Create transaction record
                    InventoryTransaction.objects.create(
                        shop_inventory=shop_inventory,
                        transaction_type='STOCK_IN',
                        quantity=quantity,
                        unit_cost=frame.price,
                        created_by=request.user,
                        notes=f"CSV upload - Row {row_num}"
                    )
                    
                    processed_items.append({
                        'frame_id': frame_id,
                        'frame_name': frame.name,
                        'quantity_added': quantity,
                        'inventory_created': created,
                        'row_number': row_num
                    })
                
                if errors:
                    return Response({
                        'error': 'CSV processing had errors',
                        'errors': errors,
                        'processed_items_count': len(processed_items)
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                return Response({
                    'message': f'Successfully processed {len(processed_items)} items',
                    'processed_items': processed_items,
                    'shop_name': shop.name
                }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response(
                {'error': f'Failed to process CSV: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ShopBillingReportView(APIView):
    """
    Generate a billing report for a specific shop for the current month.
    """
    permission_classes = [IsAuthenticated, IsDistributor]

    def get(self, request, shop_id):
        try:
            shop = Shop.objects.get(id=shop_id)
        except Shop.DoesNotExist:
            return Response(
                {'error': 'Shop not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get date range for the current month
        today = timezone.now()
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_of_month = (start_of_month + timezone.timedelta(days=32)).replace(day=1) - timezone.timedelta(seconds=1)

        # Get all SALE transactions for the shop in the current month
        sales_transactions = InventoryTransaction.objects.filter(
            shop_inventory__shop=shop,
            transaction_type=InventoryTransaction.TransactionType.SALE,
            created_at__range=(start_of_month, end_of_month)
        ).select_related('shop_inventory__frame')

        # Aggregate sales data by frame
        bill_items = {}
        total_amount_due = 0

        for trans in sales_transactions:
            frame = trans.shop_inventory.frame
            quantity_sold = abs(trans.quantity)
            cost = trans.unit_cost * quantity_sold if trans.unit_cost else 0
            
            if frame.id not in bill_items:
                bill_items[frame.id] = {
                    'frame_id': frame.product_id,
                    'frame_name': frame.name,
                    'quantity_sold': 0,
                    'total_cost': 0,
                }
            
            bill_items[frame.id]['quantity_sold'] += quantity_sold
            bill_items[frame.id]['total_cost'] += cost
            total_amount_due += cost
            
        return Response({
            'shop_name': shop.name,
            'month': start_of_month.strftime('%B %Y'),
            'total_amount_due': total_amount_due,
            'items': list(bill_items.values())
        })
