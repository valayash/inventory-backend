from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import UserInfoView

router = DefaultRouter()
# Future user authentication endpoints can be registered here

urlpatterns = [
    path('user-info/', UserInfoView.as_view(), name='user-info'),
] + router.urls 