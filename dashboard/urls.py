from django.urls import path
from .views import (
    SalesTrendsView, TopProductsView, TopProductsWithLensView, SlowMovingInventoryView,
    ShopPerformanceComparisonView, RevenueSummaryView, LowStockAlertsView, SalesReportView,
    
    # Shop Owner Views
    ShopSalesSummaryView, ShopTopSellingProductsView,
    ShopSalesTrendsView, ShopTopProductsWithLensView, ShopSlowMovingInventoryView,
    ShopLowStockAlertsView, ShopSalesReportView
)

urlpatterns = [
    # Distributor Dashboard Endpoints
    path('sales-trends/', SalesTrendsView.as_view(), name='sales-trends'),
    path('top-products/', TopProductsView.as_view(), name='top-products'),
    path('top-products-with-lens/', TopProductsWithLensView.as_view(), name='top-products-with-lens'),
    path('slow-moving-inventory/', SlowMovingInventoryView.as_view(), name='slow-moving-inventory'),
    path('shop-performance/', ShopPerformanceComparisonView.as_view(), name='shop-performance'),
    path('revenue-summary/', RevenueSummaryView.as_view(), name='revenue-summary'),
    path('low-stock-alerts/', LowStockAlertsView.as_view(), name='low-stock-alerts'),
    path('sales-report/', SalesReportView.as_view(), name='sales-report'),
    
    # Shop Owner Dashboard Endpoints
    path('shop/summary/', ShopSalesSummaryView.as_view(), name='shop-sales-summary'),
    path('shop/top-products/', ShopTopSellingProductsView.as_view(), name='shop-top-products'),
    path('shop/sales-trends/', ShopSalesTrendsView.as_view(), name='shop-sales-trends'),
    path('shop/top-products-with-lens/', ShopTopProductsWithLensView.as_view(), name='shop-top-products-with-lens'),
    path('shop/slow-moving-inventory/', ShopSlowMovingInventoryView.as_view(), name='shop-slow-moving-inventory'),
    path('shop/low-stock-alerts/', ShopLowStockAlertsView.as_view(), name='shop-low-stock-alerts'),
    path('shop/sales-report/', ShopSalesReportView.as_view(), name='shop-sales-report'),
] 