from datetime import datetime, timedelta
from django.db.models import Count, Sum, F
from django.db.models.functions import TruncDay, TruncMonth, TruncWeek
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from inventory.models import ShopInventory, InventoryTransaction
from inventory_system.permissions import IsShopOwner
from django.db import models


class ShopSalesSummaryView(APIView):
    """
    Key statistics for the current shop owner's shop for the current month.
    """
    permission_classes = [IsAuthenticated, IsShopOwner]

    def get(self, request):
        # Get the current month start and end dates
        now = timezone.now()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Get sales for current user's shop this month from transactions
        sales_transactions = InventoryTransaction.objects.filter(
            shop_inventory__shop=request.user.shop,
            transaction_type=InventoryTransaction.TransactionType.SALE,
            created_at__gte=current_month_start
        )
        
        # Calculate statistics from transactions
        total_sales_current_month = sales_transactions.aggregate(
            count=Sum('quantity')
        )['count'] or 0
        total_sales_current_month = abs(total_sales_current_month) # quantity is negative for sales

        total_revenue_current_month = sales_transactions.aggregate(
            total=Sum(F('quantity') * F('unit_price'), output_field=models.DecimalField())
        )['total'] or 0
        total_revenue_current_month = abs(total_revenue_current_month)

        # Count items in stock for this shop using the correct model
        items_in_stock = ShopInventory.objects.filter(
            shop=request.user.shop
        ).aggregate(
            total_items=Sum('quantity_received') - Sum('quantity_sold')
        )['total_items'] or 0
        
        return Response({
            'total_sales_current_month': total_sales_current_month,
            'total_revenue_current_month': str(total_revenue_current_month),
            'items_in_stock': items_in_stock,
            'shop_name': request.user.shop.name
        })


class ShopTopSellingProductsView(APIView):
    """
    Top 5 selling products for the current shop owner's shop, with revenue.
    """
    permission_classes = [IsAuthenticated, IsShopOwner]

    def get(self, request):
        limit = int(request.query_params.get('limit', 10))
        # Get top selling frames for this shop
        top_products = (
            InventoryTransaction.objects
            .filter(
                shop_inventory__shop=request.user.shop,
                transaction_type=InventoryTransaction.TransactionType.SALE
            )
            .values('shop_inventory__frame__name', 'shop_inventory__frame__product_id')
            .annotate(
                sales_count=Sum(F('quantity') * -1),
                total_revenue=Sum(F('quantity') * F('unit_price') * -1, output_field=models.DecimalField())
            )
            .order_by('-sales_count')[:limit]
        )
        
        # Format the response
        products_data = []
        for product in top_products:
            products_data.append({
                'frame_name': product['shop_inventory__frame__name'],
                'product_id': product['shop_inventory__frame__product_id'],
                'sales_count': product['sales_count'],
                'total_revenue': float(product['total_revenue'] or 0)
            })
        
        return Response({
            'top_products': products_data,
            'shop_name': request.user.shop.name
        })


class ShopSalesByDayView(APIView):
    """
    Sales for the current shop grouped by day for the last 30 days.
    """
    permission_classes = [IsAuthenticated, IsShopOwner]

    def get(self, request):
        # Calculate 30 days ago from today
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # Get sales for this shop from last 30 days, grouped by day
        sales_by_day = (
            InventoryTransaction.objects
            .filter(
                shop_inventory__shop=request.user.shop,
                transaction_type=InventoryTransaction.TransactionType.SALE,
                created_at__gte=thirty_days_ago
            )
            .annotate(day=TruncDay('created_at'))
            .values('day')
            .annotate(sales_count=Count('id'))
            .order_by('day')
        )
        
        # Format the response
        daily_sales = []
        for item in sales_by_day:
            daily_sales.append({
                'date': item['day'].strftime('%Y-%m-%d'),
                'sales_count': item['sales_count']
            })
        
        return Response({
            'daily_sales': daily_sales,
            'shop_name': request.user.shop.name,
            'period_days': 30
        })


# Shop Owner Analytics Views

class ShopSalesTrendsView(APIView):
    """
    Sales trends for the current shop owner, filterable by period.
    """
    permission_classes = [IsAuthenticated, IsShopOwner]

    def get(self, request):
        period = request.query_params.get('period', 'month')
        if period not in ['day', 'week', 'month']:
            period = 'month'
        
        if period == 'day':
            trunc_func = TruncDay
        elif period == 'week':
            trunc_func = TruncWeek
        else:
            trunc_func = TruncMonth

        sales_trends = (
            InventoryTransaction.objects.filter(
                shop_inventory__shop=request.user.shop,
                transaction_type=InventoryTransaction.TransactionType.SALE
            )
            .annotate(period=trunc_func('created_at'))
            .values('period')
            .annotate(
                sales_count=Sum(F('quantity') * -1),
                total_revenue=Sum(F('quantity') * F('unit_price') * -1, output_field=models.DecimalField())
            )
            .order_by('period')
        )
        
        trends_data = []
        for item in sales_trends:
            period_str = item['period'].strftime('%Y-%m-%d')
            if period == 'month':
                period_str = item['period'].strftime('%Y-%m')
            elif period == 'week':
                period_str = f"{item['period'].strftime('%Y-W%U')}"
            
            trends_data.append({
                'period': period_str,
                'sales_count': item['sales_count'],
                'total_revenue': float(item['total_revenue'] or 0)
            })
        
        return Response({
            'period': period,
            'trends': trends_data
        })


class ShopTopProductsWithLensView(APIView):
    """
    Top selling frames and lens combinations for the current shop.
    """
    permission_classes = [IsAuthenticated, IsShopOwner]

    def get(self, request):
        limit = int(request.query_params.get('limit', 10))
        
        # As with the distributor view, this is simplified post-refactor.
        top_products = (
            InventoryTransaction.objects.filter(
                shop_inventory__shop=request.user.shop,
                transaction_type=InventoryTransaction.TransactionType.SALE
            )
            .values(
                'shop_inventory__frame__name', 
                'shop_inventory__frame__product_id'
            )
            .annotate(
                sales_count=Sum(F('quantity') * -1),
                total_revenue=Sum(F('quantity') * F('unit_price') * -1, output_field=models.DecimalField())
            )
            .order_by('-sales_count')[:limit]
        )
        
        combinations_data = []
        for product in top_products:
            combinations_data.append({
                'frame_name': product['shop_inventory__frame__name'],
                'product_id': product['shop_inventory__frame__product_id'],
                'lens_type': 'N/A',
                'sales_count': product['sales_count'],
                'total_revenue': float(product['total_revenue'] or 0)
            })
        
        return Response({
            'top_combinations': combinations_data
        })


class ShopSlowMovingInventoryView(APIView):
    """
    Slow moving inventory for the current shop.
    """
    permission_classes = [IsAuthenticated, IsShopOwner]

    def get(self, request):
        days_threshold = int(request.query_params.get('days', 90))
        threshold_date = timezone.now() - timedelta(days=days_threshold)
        
        slow_moving_items = (
            ShopInventory.objects.filter(
                shop=request.user.shop,
                last_restocked__lt=threshold_date
            )
            .select_related('frame')
            .order_by('last_restocked')
        )
        
        items_data = []
        for item in slow_moving_items:
            days_since_restock = (timezone.now().date() - item.last_restocked).days
            items_data.append({
                'shop_inventory_id': item.id,
                'frame_name': item.frame.name,
                'product_id': item.frame.product_id,
                'frame_price': float(item.frame.price),
                'quantity_remaining': item.quantity_remaining,
                'last_restocked': item.last_restocked.strftime('%Y-%m-%d'),
                'days_since_restock': days_since_restock
            })
        
        return Response({
            'slow_moving_items': items_data,
            'total_count': len(items_data),
            'threshold_days': days_threshold
        })


class ShopLowStockAlertsView(APIView):
    """
    Low stock alerts for the current shop.
    """
    permission_classes = [IsAuthenticated, IsShopOwner]

    def get(self, request):
        threshold = int(request.query_params.get('threshold', 5))
        
        low_stock_items = (
            ShopInventory.objects
            .filter(shop=request.user.shop)
            .annotate(rem_quantity=F('quantity_received') - F('quantity_sold'))
            .filter(rem_quantity__lt=threshold)
            .select_related('frame')
            .order_by('rem_quantity')
        )
        
        items_data = []
        for item in low_stock_items:
            items_data.append({
                'frame_name': item.frame.name,
                'product_id': item.frame.product_id,
                'quantity_remaining': item.rem_quantity,
                'quantity_sold': item.quantity_sold,
                'quantity_received': item.quantity_received,
                'frame_price': float(item.frame.price),
                'last_restocked': item.last_restocked.strftime('%Y-%m-%d')
            })

        return Response({
            'threshold': threshold,
            'low_stock_items': items_data,
            'total_count': len(items_data)
        })


class ShopSalesReportView(APIView):
    """
    Monthly/quarterly sales reports for the current shop.
    """
    permission_classes = [IsAuthenticated, IsShopOwner]

    def get(self, request):
        report_type = request.query_params.get('type', 'monthly')
        year = int(request.query_params.get('year', timezone.now().year))
        
        if report_type == 'quarterly':
            quarters = []
            for quarter in range(1, 5):
                start_month = (quarter - 1) * 3 + 1
                end_month = quarter * 3
                start_date = datetime(year, start_month, 1)
                end_date = datetime(year, end_month + 1, 1) if end_month < 12 else datetime(year + 1, 1, 1)

                quarter_sales = InventoryTransaction.objects.filter(
                    shop_inventory__shop=request.user.shop,
                    transaction_type=InventoryTransaction.TransactionType.SALE,
                    created_at__gte=start_date,
                    created_at__lt=end_date
                )
                
                stats = quarter_sales.aggregate(
                    total_sales=Sum(F('quantity') * -1),
                    total_revenue=Sum(F('quantity') * F('unit_price') * -1, output_field=models.DecimalField())
                )
                avg_sale_value = (stats['total_revenue'] / stats['total_sales']) if stats['total_sales'] else 0
                
                quarters.append({
                    'quarter': quarter,
                    'period': f'Q{quarter} {year}',
                    'total_sales': stats['total_sales'] or 0,
                    'total_revenue': float(stats['total_revenue'] or 0),
                    'avg_sale_value': float(avg_sale_value or 0)
                })
            
            return Response({
                'report_type': 'quarterly',
                'year': year,
                'quarters': quarters
            })
        
        else:
            months = []
            for month in range(1, 13):
                start_date = datetime(year, month, 1)
                end_date = datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)

                month_sales = InventoryTransaction.objects.filter(
                    shop_inventory__shop=request.user.shop,
                    transaction_type=InventoryTransaction.TransactionType.SALE,
                    created_at__gte=start_date,
                    created_at__lt=end_date
                )
                
                stats = month_sales.aggregate(
                    total_sales=Sum(F('quantity') * -1),
                    total_revenue=Sum(F('quantity') * F('unit_price') * -1, output_field=models.DecimalField())
                )
                avg_sale_value = (stats['total_revenue'] / stats['total_sales']) if stats['total_sales'] else 0
                
                months.append({
                    'month': month,
                    'period': start_date.strftime('%B %Y'),
                    'total_sales': stats['total_sales'] or 0,
                    'total_revenue': float(stats['total_revenue'] or 0),
                    'avg_sale_value': float(avg_sale_value or 0)
                })
            
            return Response({
                'report_type': 'monthly',
                'year': year,
                'months': months
            })
