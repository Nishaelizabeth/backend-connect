"""
Travel Store Serializers.
"""

from rest_framework import serializers
from .models import (
    Product, 
    ProductCategory, 
    Wishlist, 
    Cart, 
    CartItem, 
    Order, 
    OrderItem
)


class ProductCategorySerializer(serializers.ModelSerializer):
    """Serializer for product categories."""
    
    class Meta:
        model = ProductCategory
        fields = ['id', 'name', 'icon']


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for products."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    in_stock = serializers.BooleanField(read_only=True)
    is_wishlisted = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'stock_quantity',
            'image', 'category', 'category_name', 'rating', 'in_stock',
            'is_wishlisted', 'created_at'
        ]

    def get_is_wishlisted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Wishlist.objects.filter(
                user=request.user, 
                product=obj
            ).exists()
        return False


class ProductDetailSerializer(ProductSerializer):
    """Detailed product serializer with category info."""
    
    category = ProductCategorySerializer(read_only=True)

    class Meta(ProductSerializer.Meta):
        fields = ProductSerializer.Meta.fields


class WishlistSerializer(serializers.ModelSerializer):
    """Serializer for wishlist items."""
    
    product = ProductSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Wishlist
        fields = ['id', 'product', 'product_id', 'created_at']

    def validate_product_id(self, value):
        if not Product.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Product not found or unavailable.")
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        product_id = validated_data['product_id']
        
        # Check if already wishlisted
        wishlist_item, created = Wishlist.objects.get_or_create(
            user=user,
            product_id=product_id
        )
        
        if not created:
            raise serializers.ValidationError("Product already in wishlist.")
        
        return wishlist_item


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for cart items."""
    
    product = ProductSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True, required=False)
    subtotal = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True
    )

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity', 'subtotal']


class CartSerializer(serializers.ModelSerializer):
    """Serializer for the shopping cart."""
    
    items = CartItemSerializer(many=True, read_only=True)
    total_amount = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True
    )
    total_items = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_amount', 'total_items', 'updated_at']


class AddToCartSerializer(serializers.Serializer):
    """Serializer for adding items to cart."""
    
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)

    def validate_product_id(self, value):
        try:
            product = Product.objects.get(id=value, is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found or unavailable.")
        return value

    def validate(self, data):
        product = Product.objects.get(id=data['product_id'])
        quantity = data.get('quantity', 1)
        
        # Check stock
        user = self.context['request'].user
        cart, _ = Cart.objects.get_or_create(user=user)
        
        existing_item = cart.items.filter(product_id=data['product_id']).first()
        current_qty = existing_item.quantity if existing_item else 0
        
        if current_qty + quantity > product.stock_quantity:
            raise serializers.ValidationError({
                'quantity': f'Only {product.stock_quantity - current_qty} items available.'
            })
        
        return data


class UpdateCartSerializer(serializers.Serializer):
    """Serializer for updating cart item quantity."""
    
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=0)

    def validate(self, data):
        product_id = data['product_id']
        quantity = data['quantity']
        
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError({
                'product_id': 'Product not found.'
            })
        
        if quantity > product.stock_quantity:
            raise serializers.ValidationError({
                'quantity': f'Only {product.stock_quantity} items available.'
            })
        
        return data


class RemoveFromCartSerializer(serializers.Serializer):
    """Serializer for removing items from cart."""
    
    product_id = serializers.IntegerField()


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for order items."""
    
    subtotal = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True
    )

    class Meta:
        model = OrderItem
        fields = ['id', 'product_name', 'quantity', 'price', 'subtotal']


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for orders."""
    
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'total_amount', 'status', 'shipping_address',
            'items', 'created_at'
        ]


class CheckoutSerializer(serializers.Serializer):
    """Serializer for checkout process."""
    
    shipping_address = serializers.CharField(max_length=500, required=False, default='')

    def validate(self, data):
        user = self.context['request'].user
        
        try:
            cart = Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            raise serializers.ValidationError("Cart is empty.")
        
        if not cart.items.exists():
            raise serializers.ValidationError("Cart is empty.")
        
        # Validate stock for all items
        for item in cart.items.all():
            if item.quantity > item.product.stock_quantity:
                raise serializers.ValidationError({
                    'stock': f'Not enough stock for {item.product.name}. Only {item.product.stock_quantity} available.'
                })
        
        return data
