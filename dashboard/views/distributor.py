from datetime import datetime, timedelta
from django.db.models import Count, Sum, Avg, Max, Min, F, Q
from django.db.models.functions import Trunc, TruncDay, TruncMonth, TruncWeek
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from inventory.models import ShopInventory, ShopFinancialSummary, InventoryTransaction
from shops.models import Shop
from products.models import Frame
from inventory_system.permissions import IsDistributor
from django.db import models


class SalesTrendsView(APIView):
    """
    Sales trends grouped by month or day for distributor analytics.
    """
    permission_classes = [IsAuthenticated, IsDistributor]

    def get(self, request):
        # Get period parameter (default to 'month')
        period = request.query_params.get('period', 'month')
        
        if period not in ['day', 'month', 'week']:
            period = 'month'
        
        # Group sales by the specified period and count/sum revenue
        if period == 'day':
            trunc_func = TruncDay
        elif period == 'week':
            trunc_func = TruncWeek
        else:
            trunc_func = TruncMonth
        
        sales_trends = (
            InventoryTransaction.objects
            .filter(transaction_type=InventoryTransaction.TransactionType.SALE)
            .annotate(period=trunc_func('created_at'))
            .values('period')
            .annotate(
                sales_count=Sum(F('quantity') * -1),
                total_revenue=Sum(F('quantity') * F('unit_price') * -1, output_field=models.DecimalField())
            )
            .order_by('period')
        )
        
        # Format the response
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


class TopProductsView(APIView):
    """
    Top selling products (frames) with sale counts for distributor analytics.
    """
    permission_classes = [IsAuthenticated, IsDistributor]

    def get(self, request):
        # Get limit parameter (default to 10)
        limit = int(request.query_params.get('limit', 10))
        
        # Get top selling frames by counting sales
        top_products = (
            InventoryTransaction.objects
            .filter(transaction_type=InventoryTransaction.TransactionType.SALE)
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
            'top_products': products_data
        })


class TopProductsWithLensView(APIView):
    """
    Top selling frames and lens combinations for distributor analytics.
    """
    permission_classes = [IsAuthenticated, IsDistributor]

    def get(self, request):
        # This view is now more complex as we don't have a direct link to lens_type in transactions
        # For now, we will return top products without lens information.
        # A more sophisticated solution would require model changes.
        limit = int(request.query_params.get('limit', 10))
        
        top_products = (
            InventoryTransaction.objects
            .filter(transaction_type=InventoryTransaction.TransactionType.SALE)
            .values('shop_inventory__frame__name', 'shop_inventory__frame__product_id')
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
                'lens_type': 'N/A', # Lens data not available in transaction
                'sales_count': product['sales_count'],
                'total_revenue': float(product['total_revenue'] or 0)
            })
        
        return Response({
            'top_combinations': combinations_data
        })


class SlowMovingInventoryView(APIView):
    """
    Slow moving inventory items that have not been restocked recently.
    """
    permission_classes = [IsAuthenticated, IsDistributor]

    def get(self, request):
        days_threshold = int(request.query_params.get('days', 90))
        threshold_date = timezone.now() - timedelta(days=days_threshold)
        
        # Find inventory that hasn't been restocked in a while
        slow_moving_items = (
            ShopInventory.objects
            .filter(last_restocked__lt=threshold_date)
            .select_related('frame', 'shop')
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
                'shop_name': item.shop.name,
                'shop_id': item.shop.id,
                'quantity_remaining': item.quantity_remaining,
                'last_restocked': item.last_restocked.strftime('%Y-%m-%d'),
                'days_since_restock': days_since_restock
            })
        
        return Response({
            'slow_moving_items': items_data,
            'total_count': len(items_data),
            'threshold_days': days_threshold
        })


class ShopPerformanceComparisonView(APIView):
    """
    Compare performance of all shops with sales, revenue, and inventory metrics.
    """
    permission_classes = [IsAuthenticated, IsDistributor]

    def get(self, request):
        # Get time period (default to current month)
        period = request.query_params.get('period', 'month')  # month, quarter, year
        
        # Calculate date range
        now = timezone.now()
        if period == 'quarter':
            # Current quarter
            quarter = (now.month - 1) // 3 + 1
            start_date = now.replace(month=(quarter - 1) * 3 + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == 'year':
            # Current year
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            # Current month
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Get all shops with their performance metrics
        shops = Shop.objects.all()
        shop_performance = []
        
        for shop in shops:
            # Sales metrics for the period
            sales_in_period = InventoryTransaction.objects.filter(
                shop_inventory__shop=shop,
                transaction_type=InventoryTransaction.TransactionType.SALE,
                created_at__gte=start_date
            )
            
            # Current inventory metrics
            inventory_items = ShopInventory.objects.filter(shop=shop)
            
            # Calculate metrics
            total_sales = sales_in_period.aggregate(Sum('quantity'))['quantity__sum'] or 0
            total_sales = abs(total_sales)

            total_revenue = sales_in_period.aggregate(
                total=Sum(F('quantity') * F('unit_price'), output_field=models.DecimalField())
            )['total'] or 0
            total_revenue = abs(total_revenue)

            avg_sale_value = total_revenue / total_sales if total_sales > 0 else 0
            
            # Inventory metrics
            total_inventory_value = sum(
                item.quantity_remaining * item.frame.price for item in inventory_items
            )
            total_items_in_stock = sum(item.quantity_remaining for item in inventory_items)
            low_stock_items = inventory_items.filter(
                quantity_received__lt=F('quantity_sold') + 5
            ).count()
            
            # Financial summary
            current_month_summary = ShopFinancialSummary.objects.filter(
                shop=shop,
                month__gte=start_date.date()
            ).aggregate(
                total_profit=Sum('total_profit'),
                total_cost=Sum('total_cost')
            )
            
            shop_performance.append({
                'shop_id': shop.id,
                'shop_name': shop.name,
                'owner_name': shop.owner_name,
                'total_sales': total_sales,
                'total_revenue': float(total_revenue),
                'avg_sale_value': float(avg_sale_value),
                'total_inventory_value': float(total_inventory_value),
                'total_items_in_stock': total_items_in_stock,
                'low_stock_items': low_stock_items,
                'total_profit': float(current_month_summary['total_profit'] or 0),
                'total_cost': float(current_month_summary['total_cost'] or 0)
            })
        
        # Sort by total revenue (descending)
        shop_performance.sort(key=lambda x: x['total_revenue'], reverse=True)
        
        return Response({
            'period': period,
            'shop_performance': shop_performance
        })


class RevenueSummaryView(APIView):
    """
    Revenue summaries by shop and overall totals.
    """
    permission_classes = [IsAuthenticated, IsDistributor]

    def get(self, request):
        # Get time period
        period = request.query_params.get('period', 'month')
        
        # Calculate date range
        now = timezone.now()
        if period == 'quarter':
            quarter = (now.month - 1) // 3 + 1
            start_date = now.replace(month=(quarter - 1) * 3 + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == 'year':
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Overall summary
        overall_stats = InventoryTransaction.objects.filter(
            transaction_type=InventoryTransaction.TransactionType.SALE,
            created_at__gte=start_date
        ).aggregate(
            total_sales=Sum(F('quantity') * -1),
            total_revenue=Sum(F('quantity') * F('unit_price') * -1, output_field=models.DecimalField())
        )
        avg_sale_value = (overall_stats['total_revenue'] / overall_stats['total_sales']) if overall_stats['total_sales'] else 0

        # Revenue by shop
        shop_revenue = (
            InventoryTransaction.objects
            .filter(
                transaction_type=InventoryTransaction.TransactionType.SALE,
                created_at__gte=start_date
            )
            .values('shop_inventory__shop__name', 'shop_inventory__shop__id')
            .annotate(
                total_sales=Sum(F('quantity') * -1),
                total_revenue=Sum(F('quantity') * F('unit_price') * -1, output_field=models.DecimalField())
            )
            .order_by('-total_revenue')
        )
        
        # Revenue by month/period trend
        revenue_trends = (
            InventoryTransaction.objects
            .filter(
                transaction_type=InventoryTransaction.TransactionType.SALE,
                created_at__gte=start_date
            )
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(
                total_sales=Sum(F('quantity') * -1),
                total_revenue=Sum(F('quantity') * F('unit_price') * -1, output_field=models.DecimalField())
            )
            .order_by('month')
        )
        
        # Format response
        shop_data = []
        for shop in shop_revenue:
            shop_data.append({
                'shop_id': shop['shop_inventory__shop__id'],
                'shop_name': shop['shop_inventory__shop__name'],
                'total_sales': shop['total_sales'],
                'total_revenue': float(shop['total_revenue'] or 0),
                'avg_sale_value': (float(shop['total_revenue'] or 0) / shop['total_sales']) if shop['total_sales'] else 0
            })
        
        trend_data = []
        for trend in revenue_trends:
            trend_data.append({
                'month': trend['month'].strftime('%Y-%m'),
                'total_sales': trend['total_sales'],
                'total_revenue': float(trend['total_revenue'] or 0)
            })
        
        return Response({
            'period': period,
            'overall_summary': {
                'total_sales': overall_stats['total_sales'] or 0,
                'total_revenue': float(overall_stats['total_revenue'] or 0),
                'avg_sale_value': float(avg_sale_value or 0)
            },
            'shop_revenue': shop_data,
            'revenue_trends': trend_data
        })


class LowStockAlertsView(APIView):
    """
    Low stock alerts for all shops.
    """
    permission_classes = [IsAuthenticated, IsDistributor]

    def get(self, request):
        # Get threshold parameter (default to 5)
        threshold = int(request.query_params.get('threshold', 5))
        
        # Find low stock items by annotating with a non-conflicting name
        low_stock_items = (
            ShopInventory.objects
            .annotate(rem_quantity=F('quantity_received') - F('quantity_sold'))
            .filter(rem_quantity__lt=threshold)
            .select_related('shop', 'frame')
            .order_by('rem_quantity', 'shop__name')
        )
        
        # Group by shop
        shop_alerts = {}
        for item in low_stock_items:
            shop_name = item.shop.name
            if shop_name not in shop_alerts:
                shop_alerts[shop_name] = {
                    'shop_id': item.shop.id,
                    'shop_name': shop_name,
                    'items': []
                }
            
            shop_alerts[shop_name]['items'].append({
                'frame_name': item.frame.name,
                'product_id': item.frame.product_id,
                'quantity_remaining': item.rem_quantity,
                'quantity_sold': item.quantity_sold,
                'quantity_received': item.quantity_received,
                'frame_price': float(item.frame.price),
                'last_restocked': item.last_restocked.strftime('%Y-%m-%d')
            })
        
        # Convert to list
        alerts_list = list(shop_alerts.values())
        
        # Summary statistics
        total_low_stock_items = sum(len(alert['items']) for alert in alerts_list)
        shops_affected = len(alerts_list)
        
        return Response({
            'threshold': threshold,
            'summary': {
                'total_low_stock_items': total_low_stock_items,
                'shops_affected': shops_affected
            },
            'shop_alerts': alerts_list
        })


class SalesReportView(APIView):
    """
    Monthly/quarterly sales reports with detailed metrics.
    """
    permission_classes = [IsAuthenticated, IsDistributor]

    def get(self, request):
        # Get parameters
        report_type = request.query_params.get('type', 'monthly')  # monthly, quarterly
        year = int(request.query_params.get('year', timezone.now().year))
        
        if report_type == 'quarterly':
            # Quarterly report
            quarters = []
            for quarter in range(1, 5):
                start_month = (quarter - 1) * 3 + 1
                end_month = quarter * 3
                
                start_date = datetime(year, start_month, 1)
                if end_month == 12:
                    end_date = datetime(year + 1, 1, 1)
                else:
                    end_date = datetime(year, end_month + 1, 1)
                
                # Get sales for this quarter
                quarter_sales = InventoryTransaction.objects.filter(
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
            # Monthly report
            months = []
            for month in range(1, 13):
                start_date = datetime(year, month, 1)
                if month == 12:
                    end_date = datetime(year + 1, 1, 1)
                else:
                    end_date = datetime(year, month + 1, 1)
                
                # Get sales for this month
                month_sales = InventoryTransaction.objects.filter(
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
