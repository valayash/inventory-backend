from rest_framework.routers import DefaultRouter
from .views import FrameViewSet, LensTypeViewSet

router = DefaultRouter()
router.register(r'frames', FrameViewSet, basename='frame')
router.register(r'lens-types', LensTypeViewSet, basename='lenstype')

urlpatterns = router.urls 