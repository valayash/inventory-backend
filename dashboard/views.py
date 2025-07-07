from django.shortcuts import render
from datetime import datetime, timedelta
from django.db.models import Count, Sum
from django.db.models.functions import Trunc, TruncDay
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from sales.models import Sale
from inventory.models import InventoryItem
from inventory_system.permissions import IsDistributor, IsShopOwner


class SalesTrendsView(APIView):
    """
    Sales trends grouped by month or day for distributor analytics.
    """
    permission_classes = [IsAuthenticated, IsDistributor]

    def get(self, request):
        # Get period parameter (default to 'month')
        period = request.query_params.get('period', 'month')
        
        if period not in ['day', 'month']:
            period = 'month'
        
        # Group sales by the specified period and count
        sales_trends = (
            Sale.objects
            .annotate(period=Trunc('sale_date', period))
            .values('period')
            .annotate(count=Count('id'))
            .order_by('period')
        )
        
        # Format the response
        trends_data = []
        for item in sales_trends:
            trends_data.append({
                'period': item['period'].strftime('%Y-%m-%d' if period == 'day' else '%Y-%m'),
                'sales_count': item['count']
            })
        
        return Response({
            'period': period,
            'trends': trends_data
        })


class TopProductsView(APIView):
    """
    Top selling products (frames) with sale counts for distributor analytics.
    """
    permission_classes = [IsAuthenticated, IsDistributor]

    def get(self, request):
        # Get top selling frames by counting sales
        top_products = (
            Sale.objects
            .values('inventory_item__frame__name', 'inventory_item__frame__product_id')
            .annotate(sales_count=Count('id'))
            .order_by('-sales_count')[:5]  # Top 5 products
        )
        
        # Format the response
        products_data = []
        for product in top_products:
            products_data.append({
                'frame_name': product['inventory_item__frame__name'],
                'product_id': product['inventory_item__frame__product_id'],
                'sales_count': product['sales_count']
            })
        
        return Response({
            'top_products': products_data
        })


class SlowMovingInventoryView(APIView):
    """
    Slow moving inventory items that have been in stock for more than 90 days.
    """
    permission_classes = [IsAuthenticated, IsDistributor]

    def get(self, request):
        # Calculate 90 days ago from today
        ninety_days_ago = timezone.now() - timedelta(days=90)
        
        # Find inventory items in stock older than 90 days
        slow_moving_items = (
            InventoryItem.objects
            .filter(
                status='IN_STOCK',
                date_stocked__lt=ninety_days_ago
            )
            .select_related('frame', 'shop')
            .order_by('date_stocked')
        )
        
        # Format the response
        items_data = []
        for item in slow_moving_items:
            days_in_stock = (timezone.now() - item.date_stocked).days
            items_data.append({
                'inventory_item_id': item.id,
                'frame_name': item.frame.name,
                'product_id': item.frame.product_id,
                'frame_price': str(item.frame.price),
                'shop_name': item.shop.name,
                'shop_id': item.shop.id,
                'date_stocked': item.date_stocked.strftime('%Y-%m-%d'),
                'days_in_stock': days_in_stock
            })
        
        return Response({
            'slow_moving_items': items_data,
            'total_count': len(items_data)
        })


# Shop Owner Dashboard Views

class ShopSalesSummaryView(APIView):
    """
    Key statistics for the current shop owner's shop for the current month.
    """
    permission_classes = [IsAuthenticated, IsShopOwner]

    def get(self, request):
        # Get the current month start and end dates
        now = timezone.now()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Get sales for current user's shop this month
        current_month_sales = Sale.objects.filter(
            shop=request.user.shop,
            sale_date__gte=current_month_start
        )
        
        # Calculate statistics
        total_sales_current_month = current_month_sales.count()
        total_revenue_current_month = current_month_sales.aggregate(
            total=Sum('total_price')
        )['total'] or 0
        
        # Count items in stock for this shop
        items_in_stock = InventoryItem.objects.filter(
            shop=request.user.shop,
            status='IN_STOCK'
        ).count()
        
        return Response({
            'total_sales_current_month': total_sales_current_month,
            'total_revenue_current_month': str(total_revenue_current_month),
            'items_in_stock': items_in_stock,
            'shop_name': request.user.shop.name
        })


class ShopTopSellingProductsView(APIView):
    """
    Top 5 selling products for the current shop owner's shop.
    """
    permission_classes = [IsAuthenticated, IsShopOwner]

    def get(self, request):
        # Get top selling frames for this shop
        top_products = (
            Sale.objects
            .filter(shop=request.user.shop)
            .values('inventory_item__frame__name', 'inventory_item__frame__product_id')
            .annotate(sales_count=Count('id'))
            .order_by('-sales_count')[:5]  # Top 5 products
        )
        
        # Format the response
        products_data = []
        for product in top_products:
            products_data.append({
                'frame_name': product['inventory_item__frame__name'],
                'product_id': product['inventory_item__frame__product_id'],
                'sales_count': product['sales_count']
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
            Sale.objects
            .filter(
                shop=request.user.shop,
                sale_date__gte=thirty_days_ago
            )
            .annotate(day=TruncDay('sale_date'))
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
