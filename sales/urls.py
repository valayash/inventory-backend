from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import DistributorSalesView, RecordSaleView

router = DefaultRouter()
router.register(r'distributor-sales', DistributorSalesView, basename='distributor-sales')

urlpatterns = router.urls + [
    path('record-sale/', RecordSaleView.as_view(), name='record-sale'),
] 