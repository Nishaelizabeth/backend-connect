"""
Travel Store Views.

API endpoints for the ecommerce store functionality.
"""

import logging
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.db.models import Q

from .models import (
    Product,
    ProductCategory,
    Wishlist,
    Cart,
    CartItem,
    Order,
    OrderItem
)
from .serializers import (
    ProductSerializer,
    ProductDetailSerializer,
    ProductCategorySerializer,
    WishlistSerializer,
    CartSerializer,
    CartItemSerializer,
    AddToCartSerializer,
    UpdateCartSerializer,
    RemoveFromCartSerializer,
    OrderSerializer,
    CheckoutSerializer
)

logger = logging.getLogger(__name__)


class ProductCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for product categories.
    
    GET /api/store/categories/
    GET /api/store/categories/<id>/
    """
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    permission_classes = [permissions.IsAuthenticated]


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for products.
    
    GET /api/store/products/
    Query params: ?search=, ?category=, ?sort=price_low|price_high|rating
    
    GET /api/store/products/<id>/
    """
    queryset = Product.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Search
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Category filter
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        
        # Sorting
        sort = self.request.query_params.get('sort', '')
        if sort == 'price_low':
            queryset = queryset.order_by('price')
        elif sort == 'price_high':
            queryset = queryset.order_by('-price')
        elif sort == 'rating':
            queryset = queryset.order_by('-rating')
        else:
            queryset = queryset.order_by('-created_at')
        
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })


class WishlistViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user's wishlist.
    
    GET /api/store/wishlist/
    POST /api/store/wishlist/
    DELETE /api/store/wishlist/<id>/
    """
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'delete']

    def get_queryset(self):
        return Wishlist.objects.filter(
            user=self.request.user
        ).select_related('product', 'product__category')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })

    def perform_create(self, serializer):
        serializer.save()


class CartView(APIView):
    """
    GET /api/store/cart/
    
    Retrieve the current user's cart.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)


class CartAddView(APIView):
    """
    POST /api/store/cart/add/
    
    Add item to cart.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = AddToCartSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data.get('quantity', 1)
        
        cart, _ = Cart.objects.get_or_create(user=request.user)
        
        # Add or update cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product_id=product_id,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        return Response({
            'message': 'Item added to cart',
            'cart': CartSerializer(cart).data
        }, status=status.HTTP_200_OK)


class CartUpdateView(APIView):
    """
    PATCH /api/store/cart/update/
    
    Update item quantity in cart.
    """
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        serializer = UpdateCartSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data['quantity']
        
        try:
            cart = Cart.objects.get(user=request.user)
            cart_item = cart.items.get(product_id=product_id)
        except (Cart.DoesNotExist, CartItem.DoesNotExist):
            return Response(
                {'error': 'Item not in cart'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if quantity == 0:
            cart_item.delete()
        else:
            cart_item.quantity = quantity
            cart_item.save()
        
        return Response({
            'message': 'Cart updated',
            'cart': CartSerializer(cart).data
        }, status=status.HTTP_200_OK)


class CartRemoveView(APIView):
    """
    DELETE /api/store/cart/remove/
    
    Remove item from cart.
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        serializer = RemoveFromCartSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        product_id = serializer.validated_data['product_id']
        
        try:
            cart = Cart.objects.get(user=request.user)
            cart_item = cart.items.get(product_id=product_id)
            cart_item.delete()
        except (Cart.DoesNotExist, CartItem.DoesNotExist):
            return Response(
                {'error': 'Item not in cart'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response({
            'message': 'Item removed from cart',
            'cart': CartSerializer(cart).data
        }, status=status.HTTP_200_OK)


class CheckoutView(APIView):
    """
    POST /api/store/checkout/
    
    Process checkout and create an order (mock payment).
    """
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = CheckoutSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        cart = Cart.objects.get(user=request.user)
        shipping_address = serializer.validated_data.get('shipping_address', '')
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            total_amount=cart.total_amount,
            status=Order.Status.PAID,  # Mock payment - auto succeed
            shipping_address=shipping_address
        )
        
        # Create order items and deduct stock
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                product_name=cart_item.product.name,
                quantity=cart_item.quantity,
                price=cart_item.product.price
            )
            
            # Deduct stock
            product = cart_item.product
            product.stock_quantity -= cart_item.quantity
            product.save()
        
        # Clear cart
        cart.items.all().delete()
        
        logger.info(f"Order #{order.id} created for user {request.user.email}")
        
        return Response({
            'status': 'success',
            'message': 'Order placed successfully!',
            'order_id': order.id,
            'order': OrderSerializer(order).data
        }, status=status.HTTP_201_CREATED)


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for user's orders.
    
    GET /api/store/orders/
    GET /api/store/orders/<id>/
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(
            user=self.request.user
        ).prefetch_related('items')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })
