"""
Travel Store URL Configuration.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ProductViewSet,
    ProductCategoryViewSet,
    WishlistViewSet,
    CartView,
    CartAddView,
    CartUpdateView,
    CartRemoveView,
    CheckoutView,
    OrderViewSet
)

app_name = 'store'

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'categories', ProductCategoryViewSet, basename='category')
router.register(r'wishlist', WishlistViewSet, basename='wishlist')
router.register(r'orders', OrderViewSet, basename='order')

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
    
    # Cart endpoints
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/add/', CartAddView.as_view(), name='cart-add'),
    path('cart/update/', CartUpdateView.as_view(), name='cart-update'),
    path('cart/remove/', CartRemoveView.as_view(), name='cart-remove'),
    
    # Checkout
    path('checkout/', CheckoutView.as_view(), name='checkout'),
]
