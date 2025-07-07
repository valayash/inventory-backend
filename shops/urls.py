from rest_framework.routers import DefaultRouter
from .views import ShopViewSet

router = DefaultRouter()
router.register(r'shops', ShopViewSet, basename='shop')

urlpatterns = router.urls 