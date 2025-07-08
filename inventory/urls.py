from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import distributor, shop_owner, shared

router = DefaultRouter()

# New inventory system endpoints
router.register(r'shop-inventory', shared.ShopInventoryViewSet, basename='shop-inventory')
router.register(r'financial-summary', shared.ShopFinancialSummaryViewSet, basename='financial-summary')
router.register(r'transactions', shared.InventoryTransactionViewSet, basename='inventory-transactions')

urlpatterns = router.urls + [
    # New inventory system endpoints
    path('stock-in/', distributor.InventoryStockInView.as_view(), name='inventory-stock-in'),
    path('process-sale/', shop_owner.InventorySaleView.as_view(), name='inventory-sale'),
    path('inventory-csv-upload/', distributor.InventoryCSVUploadView.as_view(), name='inventory-csv-upload'),
    
    # Inventory Distribution endpoints for distributors
    path('distribution/', distributor.InventoryDistributionView.as_view(), name='inventory-distribution'),
    path('distribution/bulk/', distributor.InventoryDistributionBulkView.as_view(), name='inventory-distribution-bulk'),
    path('shops/<int:shop_id>/inventory/', distributor.ShopInventoryByShopView.as_view(), name='shop-inventory-detail'),
    path('shops/<int:shop_id>/billing-report/', distributor.ShopBillingReportView.as_view(), name='shop-billing-report'),
] 