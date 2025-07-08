from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    ShopInventoryViewSet, InventoryStockView, InventoryStockInView,
    InventorySaleView, ShopFinancialSummaryViewSet, InventoryTransactionViewSet,
    ShopInventoryLegacyViewSet, InventoryDistributionView, InventoryDistributionBulkView,
    ShopInventoryByShopView, InventoryCSVUploadView, ShopBillingReportView
)

router = DefaultRouter()

# New inventory system endpoints
router.register(r'shop-inventory', ShopInventoryViewSet, basename='shop-inventory')
router.register(r'financial-summary', ShopFinancialSummaryViewSet, basename='financial-summary')
router.register(r'transactions', InventoryTransactionViewSet, basename='inventory-transactions')

# Legacy endpoint for backward compatibility
router.register(r'shop-inventory-legacy', ShopInventoryLegacyViewSet, basename='shop-inventory-legacy')

urlpatterns = router.urls + [
    # Legacy endpoint
    path('inventory-stock/', InventoryStockView.as_view(), name='inventory-stock'),
    
    # New inventory system endpoints
    path('stock-in/', InventoryStockInView.as_view(), name='inventory-stock-in'),
    path('process-sale/', InventorySaleView.as_view(), name='inventory-sale'),
    path('inventory-csv-upload/', InventoryCSVUploadView.as_view(), name='inventory-csv-upload'),
    
    # Inventory Distribution endpoints for distributors
    path('distribution/', InventoryDistributionView.as_view(), name='inventory-distribution'),
    path('distribution/bulk/', InventoryDistributionBulkView.as_view(), name='inventory-distribution-bulk'),
    path('shops/<int:shop_id>/inventory/', ShopInventoryByShopView.as_view(), name='shop-inventory-detail'),
    path('shops/<int:shop_id>/billing-report/', ShopBillingReportView.as_view(), name='shop-billing-report'),
] 