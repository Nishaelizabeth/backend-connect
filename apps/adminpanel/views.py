"""
Admin Panel API Views.

Provides dashboard statistics and CRUD endpoints for all admin-managed models.
Requires staff/superuser permissions.
"""

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Q, F
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class IsAdminUser(permissions.BasePermission):
    """Allow access only to admin/staff users."""
    def has_permission(self, request, view):
        return request.user and request.user.is_staff


# ─── Dashboard Stats ───────────────────────────────────────────────
class AdminDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request):
        from apps.trips.models import Trip
        from apps.store.models import Order
        from apps.chat.models import Message

        now = timezone.now()
        days_param = int(request.query_params.get('days', 30))
        since = now - timedelta(days=days_param)

        # Total counts
        total_users = User.objects.count()
        total_trips = Trip.objects.count()
        active_trips = Trip.objects.filter(status='planned').count()
        cancelled_trips = Trip.objects.filter(status='completed').count()

        # Orders / Revenue
        orders = Order.objects.all()
        total_revenue = orders.filter(status='paid').aggregate(
            total=Sum('total_amount'))['total'] or 0
        pending_orders = orders.filter(status='pending').count()

        # Trips booked in period
        trips_in_period = Trip.objects.filter(created_at__gte=since).count()
        prev_period_start = since - timedelta(days=days_param)
        trips_prev_period = Trip.objects.filter(
            created_at__gte=prev_period_start, created_at__lt=since).count()
        trips_change = 0
        if trips_prev_period > 0:
            trips_change = round(
                ((trips_in_period - trips_prev_period) / trips_prev_period) * 100, 1)

        # New users per month (last 6 months)
        six_months_ago = now - timedelta(days=180)
        users_per_month = (
            User.objects.filter(date_joined__gte=six_months_ago)
            .annotate(month=TruncMonth('date_joined'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )

        # Trip timeline (last 30 days)
        trip_timeline = (
            Trip.objects.filter(created_at__gte=since)
            .extra(select={'day': "DATE(created_at)"})
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )

        return Response({
            'total_users': total_users,
            'total_trips': total_trips,
            'active_trips': active_trips,
            'cancelled_trips': cancelled_trips,
            'total_revenue': float(total_revenue),
            'pending_orders': pending_orders,
            'trips_booked': trips_in_period,
            'trips_change_pct': trips_change,
            'users_per_month': [
                {'month': item['month'].strftime('%b'), 'count': item['count']}
                for item in users_per_month
            ],
            'trip_timeline': [
                {'date': str(item['day']), 'count': item['count']}
                for item in trip_timeline
            ],
        })


# ─── User Management ───────────────────────────────────────────────
class AdminUserListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request):
        from apps.trips.models import Trip
        search = request.query_params.get('search', '')
        users = User.objects.all().order_by('-date_joined')
        if search:
            users = users.filter(
                Q(email__icontains=search) | Q(full_name__icontains=search))

        users = users.annotate(trip_count=Count('created_trips'))
        data = []
        for u in users[:100]:
            data.append({
                'id': u.id,
                'email': u.email,
                'full_name': u.full_name,
                'is_active': u.is_active,
                'is_staff': u.is_staff,
                'date_joined': u.date_joined.isoformat(),
                'auth_provider': u.auth_provider,
                'trip_count': u.trip_count,
            })
        return Response(data)


class AdminUserDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request, pk):
        try:
            u = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

        return Response({
            'id': u.id,
            'email': u.email,
            'full_name': u.full_name,
            'is_active': u.is_active,
            'is_staff': u.is_staff,
            'is_superuser': u.is_superuser,
            'date_joined': u.date_joined.isoformat(),
            'auth_provider': u.auth_provider,
            'bio': u.bio,
        })

    def patch(self, request, pk):
        """Toggle user active/block status."""
        try:
            u = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

        if 'is_active' in request.data:
            u.is_active = request.data['is_active']
        if 'is_staff' in request.data:
            u.is_staff = request.data['is_staff']
        u.save()
        return Response({'status': 'updated', 'is_active': u.is_active})


# ─── Trip Monitoring ───────────────────────────────────────────────
class AdminTripListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request):
        from apps.trips.models import Trip
        search = request.query_params.get('search', '')
        status_filter = request.query_params.get('status', '')

        trips = Trip.objects.select_related('creator').all().order_by('-created_at')
        if search:
            trips = trips.filter(
                Q(title__icontains=search) | Q(destination__icontains=search))
        if status_filter:
            trips = trips.filter(status=status_filter)

        data = []
        for t in trips[:100]:
            data.append({
                'id': t.id,
                'title': t.title,
                'destination': t.display_destination,
                'start_date': t.start_date.isoformat(),
                'end_date': t.end_date.isoformat(),
                'status': t.status,
                'creator_email': t.creator.email,
                'creator_name': t.creator.full_name,
                'member_count': t.members.count(),
            })
        return Response(data)


# ─── Order Management ──────────────────────────────────────────────
class AdminOrderListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request):
        from apps.store.models import Order
        orders = Order.objects.select_related('user').all().order_by('-created_at')
        status_filter = request.query_params.get('status', '')
        if status_filter:
            orders = orders.filter(status=status_filter)

        data = []
        for o in orders[:100]:
            data.append({
                'id': o.id,
                'user_email': o.user.email,
                'user_name': o.user.full_name,
                'total_amount': float(o.total_amount),
                'status': o.status,
                'created_at': o.created_at.isoformat(),
                'item_count': o.items.count(),
            })
        return Response(data)

    def patch(self, request):
        """Update order status."""
        from apps.store.models import Order
        order_id = request.data.get('order_id')
        new_status = request.data.get('status')
        try:
            order = Order.objects.get(pk=order_id)
            order.status = new_status
            order.save()
            return Response({'status': 'updated'})
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=404)


# ─── Chat Moderation ──────────────────────────────────────────────
class AdminChatRoomListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request):
        from apps.chat.models import ChatRoom
        rooms = ChatRoom.objects.select_related('trip').all().order_by('-created_at')
        data = []
        for r in rooms[:100]:
            data.append({
                'id': r.id,
                'trip_title': r.trip.title if r.trip else 'N/A',
                'message_count': r.messages.count(),
                'created_at': r.created_at.isoformat(),
            })
        return Response(data)


class AdminMessageListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request):
        from apps.chat.models import Message
        room_id = request.query_params.get('room_id', '')
        messages = Message.objects.select_related('sender', 'room').all().order_by('-created_at')
        if room_id:
            messages = messages.filter(room_id=room_id)

        data = []
        for m in messages[:200]:
            data.append({
                'id': m.id,
                'room_id': m.room_id,
                'sender_name': m.sender.full_name if m.sender else 'System',
                'sender_email': m.sender.email if m.sender else '',
                'content': m.content[:200],
                'message_type': m.message_type,
                'is_system': m.is_system,
                'created_at': m.created_at.isoformat(),
            })
        return Response(data)


# ─── Notifications (read-only) ────────────────────────────────────
class AdminNotificationListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request):
        from apps.notifications.models import Notification
        notifications = Notification.objects.select_related('user').all().order_by('-created_at')[:100]
        data = []
        for n in notifications:
            data.append({
                'id': n.id,
                'user_email': n.user.email,
                'type': n.type,
                'message': n.message,
                'is_read': n.is_read,
                'created_at': n.created_at.isoformat(),
            })
        return Response(data)


# ─── Product Categories ───────────────────────────────────────────
class AdminCategoryListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request):
        from apps.store.models import ProductCategory
        categories = ProductCategory.objects.annotate(product_count=Count('products')).order_by('name')
        data = []
        for c in categories:
            data.append({
                'id': c.id,
                'name': c.name,
                'icon': c.icon,
                'product_count': c.product_count,
                'created_at': c.created_at.isoformat(),
            })
        return Response(data)

    def post(self, request):
        from apps.store.models import ProductCategory
        name = request.data.get('name', '').strip()
        icon = request.data.get('icon', '').strip()
        if not name:
            return Response({'error': 'Name is required'}, status=400)
        if ProductCategory.objects.filter(name__iexact=name).exists():
            return Response({'error': 'Category already exists'}, status=400)
        cat = ProductCategory.objects.create(name=name, icon=icon)
        return Response({'id': cat.id, 'name': cat.name, 'icon': cat.icon}, status=201)

    def delete(self, request):
        from apps.store.models import ProductCategory
        cat_id = request.data.get('id')
        try:
            cat = ProductCategory.objects.get(pk=cat_id)
            cat.delete()
            return Response({'status': 'deleted'})
        except ProductCategory.DoesNotExist:
            return Response({'error': 'Category not found'}, status=404)


# ─── Products ─────────────────────────────────────────────────────
class AdminProductListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request):
        from apps.store.models import Product
        search = request.query_params.get('search', '')
        category = request.query_params.get('category', '')
        active_filter = request.query_params.get('is_active', '')

        products = Product.objects.select_related('category').all().order_by('-created_at')
        if search:
            products = products.filter(
                Q(name__icontains=search) | Q(description__icontains=search))
        if category:
            products = products.filter(category_id=category)
        if active_filter:
            products = products.filter(is_active=active_filter.lower() == 'true')

        data = []
        for p in products[:100]:
            data.append({
                'id': p.id,
                'name': p.name,
                'description': p.description,
                'price': float(p.price),
                'stock_quantity': p.stock_quantity,
                'image': p.image,
                'category_id': p.category_id,
                'category': p.category.name if p.category else '',
                'rating': float(p.rating) if p.rating else 0,
                'is_active': p.is_active,
                'created_at': p.created_at.isoformat(),
            })
        return Response(data)

    def post(self, request):
        from apps.store.models import Product, ProductCategory
        name = request.data.get('name', '').strip()
        if not name:
            return Response({'error': 'Name is required'}, status=400)

        category = None
        cat_id = request.data.get('category_id')
        if cat_id:
            try:
                category = ProductCategory.objects.get(pk=cat_id)
            except ProductCategory.DoesNotExist:
                pass

        product = Product.objects.create(
            name=name,
            description=request.data.get('description', ''),
            price=request.data.get('price', 0),
            stock_quantity=request.data.get('stock_quantity', 0),
            image=request.data.get('image', ''),
            category=category,
            is_active=request.data.get('is_active', True),
        )
        return Response({
            'id': product.id,
            'name': product.name,
            'price': float(product.price),
        }, status=201)


class AdminProductDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def patch(self, request, pk):
        from apps.store.models import Product, ProductCategory
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=404)

        for field in ('name', 'description', 'price', 'stock_quantity', 'image', 'is_active'):
            if field in request.data:
                setattr(product, field, request.data[field])
        if 'category_id' in request.data:
            cat_id = request.data['category_id']
            if cat_id:
                try:
                    product.category = ProductCategory.objects.get(pk=cat_id)
                except ProductCategory.DoesNotExist:
                    pass
            else:
                product.category = None
        product.save()
        return Response({'status': 'updated'})

    def delete(self, request, pk):
        from apps.store.models import Product
        try:
            product = Product.objects.get(pk=pk)
            product.delete()
            return Response({'status': 'deleted'})
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=404)


# ─── Buddy Matches & Requests ─────────────────────────────────────
class AdminBuddyListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request):
        from apps.buddies.models import BuddyRequest
        requests = BuddyRequest.objects.select_related('sender', 'receiver').all().order_by('-created_at')
        data = []
        for b in requests[:100]:
            data.append({
                'id': b.id,
                'sender_name': b.sender.full_name,
                'sender_email': b.sender.email,
                'receiver_name': b.receiver.full_name,
                'receiver_email': b.receiver.email,
                'status': b.status,
                'created_at': b.created_at.isoformat(),
            })
        return Response(data)
