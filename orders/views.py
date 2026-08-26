# orders/views.py
import uuid
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from .models import Cart, CartItem, Order, OrderItem
from products.models import Product, ProductVariant
from .serializers import CartSerializer, OrderSerializer, CreateOrderSerializer
from firebase_admin import messaging


def send_push_notification(fcm_token, title, body):
    if not fcm_token:
        return
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=fcm_token,
    )
    try:
        messaging.send(message)
    except Exception as e:
        print(f"Ошибка отправки уведомления: {e}")


# ===== ГОСТЕВАЯ КОРЗИНА =====
class GuestCartView(APIView):
    """Гостевая корзина (без авторизации)"""
    permission_classes = [AllowAny]
    
    def get_session_id(self, request):
        session_id = request.COOKIES.get('guest_session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
        return session_id
    
    def get_or_create_cart(self, session_id):
        cart = Cart.objects.filter(session_id=session_id).first()
        if not cart:
            cart = Cart.objects.create(session_id=session_id)
        return cart
    
    def get(self, request):
        session_id = self.get_session_id(request)
        cart = self.get_or_create_cart(session_id)
        serializer = CartSerializer(cart)
        response = Response(serializer.data)
        response.set_cookie('guest_session_id', session_id, max_age=30*24*60*60)
        return response
    
    def post(self, request):
        session_id = self.get_session_id(request)
        product_id = request.data.get('product_id')
        variant_id = request.data.get('variant_id')
        quantity = int(request.data.get('quantity', 1))
        
        if not product_id:
            return Response(
                {'error': 'Не указан ID товара'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Товар не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        cart = self.get_or_create_cart(session_id)
        
        if variant_id:
            try:
                variant = ProductVariant.objects.get(id=variant_id, product=product, is_available=True)
                cart_item, created = CartItem.objects.get_or_create(
                    cart=cart,
                    product=product,
                    variant=variant,
                    defaults={'quantity': quantity}
                )
            except ProductVariant.DoesNotExist:
                return Response(
                    {'error': 'Вариация не найдена или недоступна'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity}
            )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        serializer = CartSerializer(cart)
        response = Response(serializer.data)
        response.set_cookie('guest_session_id', session_id, max_age=30*24*60*60)
        return response
    
    def put(self, request, item_id):
        session_id = self.get_session_id(request)
        cart = self.get_or_create_cart(session_id)
        
        try:
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
            quantity = int(request.data.get('quantity', 1))
            if quantity < 1:
                return Response(
                    {'error': 'Количество должно быть больше 0'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            cart_item.quantity = quantity
            cart_item.save()
        except CartItem.DoesNotExist:
            return Response(
                {'error': 'Товар не найден в корзине'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = CartSerializer(cart)
        return Response(serializer.data)
    
    def delete(self, request, item_id):
        session_id = self.get_session_id(request)
        cart = self.get_or_create_cart(session_id)
        
        try:
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
            cart_item.delete()
        except CartItem.DoesNotExist:
            return Response(
                {'error': 'Товар не найден в корзине'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = CartSerializer(cart)
        return Response(serializer.data)


# ===== АВТОРИЗОВАННАЯ КОРЗИНА =====
class CartView(generics.RetrieveAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = CartSerializer
    def get_object(self):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return cart


class AddToCartView(APIView):
    """Добавление товара в корзину"""
    permission_classes = (permissions.IsAuthenticated,)
    
    def post(self, request):
        product_id = request.data.get('product_id')
        variant_id = request.data.get('variant_id')
        quantity = int(request.data.get('quantity', 1))
        
        if not product_id:
            return Response(
                {'error': 'Не указан ID товара'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Товар не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        cart, _ = Cart.objects.get_or_create(user=request.user)
        
        if variant_id:
            from products.models import ProductVariant
            try:
                variant = ProductVariant.objects.get(id=variant_id, product=product, is_available=True)
                cart_item, created = CartItem.objects.get_or_create(
                    cart=cart,
                    product=product,
                    variant=variant,
                    defaults={'quantity': quantity}
                )
            except ProductVariant.DoesNotExist:
                return Response(
                    {'error': 'Вариация не найдена или недоступна'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity}
            )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UpdateCartItemView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    def put(self, request, item_id):
        quantity = request.data.get('quantity')
        if quantity is None or int(quantity) < 1:
            return Response(
                {'error': 'Количество должно быть больше 0'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            cart = Cart.objects.get(user=request.user)
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
            cart_item.quantity = int(quantity)
            cart_item.save()
            serializer = CartSerializer(cart)
            return Response(serializer.data)
        except Cart.DoesNotExist:
            return Response(
                {'error': 'Корзина не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )
        except CartItem.DoesNotExist:
            return Response(
                {'error': 'Товар не найден в корзине'},
                status=status.HTTP_404_NOT_FOUND
            )


class RemoveFromCartView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    def delete(self, request, item_id):
        try:
            cart = Cart.objects.get(user=request.user)
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
            cart_item.delete()
            serializer = CartSerializer(cart)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except (Cart.DoesNotExist, CartItem.DoesNotExist):
            return Response(
                {'error': 'Товар не найден в корзине'},
                status=status.HTTP_404_NOT_FOUND
            )


class ClearCartView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    def delete(self, request):
        try:
            cart = Cart.objects.get(user=request.user)
            cart.items.all().delete()
            return Response(
                {'message': 'Корзина очищена'},
                status=status.HTTP_200_OK
            )
        except Cart.DoesNotExist:
            return Response(
                {'error': 'Корзина не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )


# ===== ЗАКАЗЫ =====
class CreateOrderView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    @transaction.atomic
    def post(self, request):
        serializer = CreateOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data
        
        try:
            cart = Cart.objects.get(user=request.user)
            if not cart.items.exists():
                return Response(
                    {'error': 'Корзина пуста'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Cart.DoesNotExist:
            return Response(
                {'error': 'Корзина пуста'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        subtotal = sum(item.total for item in cart.items.all())
        delivery_type = data.get('delivery_type', 'delivery')
        delivery_cost = 0 if delivery_type == 'pickup' else (150 if subtotal < 800 else 0)
        discount = 0
        bonus_used = min(data.get('bonus_used', 0), request.user.bonus_points)
        if bonus_used > 0:
            request.user.bonus_points -= bonus_used
            request.user.save()
        total = subtotal + delivery_cost - discount - bonus_used
        
        order_number = f"NVK-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        order = Order.objects.create(
            user=request.user,
            order_number=order_number,
            delivery_address=data.get('delivery_address', ''),
            delivery_date=data.get('delivery_date'),
            delivery_time_from=data.get('delivery_time_from'),
            delivery_time_to=data.get('delivery_time_to'),
            comment=data.get('comment', ''),
            subtotal=subtotal,
            delivery_cost=delivery_cost,
            discount=discount,
            bonus_used=bonus_used,
            total_amount=total,
            payment_method=data['payment_method'],
            status='new',
            delivery_type=delivery_type,
            pickup_time=data.get('pickup_time'),
            pickup_date=data.get('pickup_date'),
        )
        
        for cart_item in cart.items.all():
            # Если у товара есть вариация — это отдельная позиция
            if cart_item.variant:
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    variant=cart_item.variant,  # ✅ Сохраняем вариацию
                    quantity=cart_item.quantity,
                    price_at_order=cart_item.variant.price,
                )
            else:
                # Если вариации нет — создаём обычную позицию
                first_variant = cart_item.product.variants.filter(is_available=True).first()
                price_at_order = first_variant.price if first_variant else cart_item.product.price or 0
                
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price_at_order=price_at_order,
                )
        
        cart.items.all().delete()
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class OrderListView(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = OrderSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_status']
    search_fields = ['order_number', 'user__username', 'user__full_name', 'user__email']
    ordering_fields = ['order_date', 'total_amount', 'status']
    ordering = ['-order_date']
    def get_queryset(self):
        if self.request.user.role == 'admin':
            return Order.objects.all()
        return Order.objects.filter(user=self.request.user)


class OrderDetailView(generics.RetrieveAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = OrderSerializer
    def get_queryset(self):
        if self.request.user.role == 'admin':
            return Order.objects.all()
        return Order.objects.filter(user=self.request.user)


class CancelOrderView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            if order.status not in ['new', 'confirmed']:
                return Response(
                    {'error': 'Заказ нельзя отменить (уже в обработке или доставлен)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            order.status = 'cancelled'
            order.save()
            return Response(OrderSerializer(order).data)
        except Order.DoesNotExist:
            return Response(
                {'error': 'Заказ не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

class UpdatePaymentStatusView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    
    def put(self, request, order_id):
        if request.user.role != 'admin':
            return Response(
                {'error': 'Только администраторы могут изменять статус оплаты'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {'error': 'Заказ не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        payment_status = request.data.get('payment_status')
        if payment_status not in ['pending', 'paid', 'failed', 'refunded']:
            return Response(
                {'error': 'Недопустимый статус оплаты'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.payment_status = payment_status
        order.save()
        
        return Response(OrderSerializer(order).data)

class UpdateOrderStatusView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    def put(self, request, order_id):
        if request.user.role != 'admin':
            return Response(
                {'error': 'Только администраторы могут изменять статус заказа'},
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {'error': 'Заказ не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        new_status = request.data.get('status')
        if new_status not in dict(Order.STATUS_CHOICES):
            return Response(
                {'error': f'Недопустимый статус. Допустимые: {", ".join(dict(Order.STATUS_CHOICES).keys())}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        order.status = new_status
        order.save()

        # ✅ Отправляем уведомление (если есть токен)
        if order.user.fcm_token:
            send_push_notification(
                order.user.fcm_token,
                f"Статус заказа #{order.order_number}",
                f"Ваш заказ теперь: {dict(Order.STATUS_CHOICES)[new_status]}"
            )
        
        # ✅ Начисляем бонусы, если статус delivered
        if new_status == 'delivered':
            from core.models import SiteSettings
            settings = SiteSettings.get_settings()
            if settings.bonus_enabled:
                bonus_for_100 = float(settings.bonus_rate)
                earned_bonus = int((order.total_amount / 100) * bonus_for_100)
                if earned_bonus > 0:
                    user = order.user
                    user.bonus_points += earned_bonus
                    user.save()
        
        # ✅ ЕДИНСТВЕННЫЙ return в конце функции
        return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)