from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


class UserInfoView(APIView):
    """
    Returns current user's information including role.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'shop_id': user.shop.id if user.shop else None,
            'shop_name': user.shop.name if user.shop else None,
        })
