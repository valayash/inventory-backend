from django.urls import path
from .views import (
    SalesTrendsView, TopProductsView, SlowMovingInventoryView,
    ShopSalesSummaryView, ShopTopSellingProductsView, ShopSalesByDayView
)

urlpatterns = [
    # Distributor Dashboard Endpoints
    path('sales-trends/', SalesTrendsView.as_view(), name='sales-trends'),
    path('top-products/', TopProductsView.as_view(), name='top-products'),
    path('slow-moving-inventory/', SlowMovingInventoryView.as_view(), name='slow-moving-inventory'),
    
    # Shop Owner Dashboard Endpoints
    path('shop/summary/', ShopSalesSummaryView.as_view(), name='shop-sales-summary'),
    path('shop/top-products/', ShopTopSellingProductsView.as_view(), name='shop-top-products'),
    path('shop/sales-by-day/', ShopSalesByDayView.as_view(), name='shop-sales-by-day'),
] 