# orders/views.py
import logging
import uuid
from decimal import Decimal

from django.utils import timezone
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from core.models import SiteSettings
from users.models import User
from .models import Cart, CartItem, Order, OrderItem, OrderStatusHistory
from products.models import Product, ProductVariant
from .serializers import CartSerializer, OrderSerializer, CreateOrderSerializer
from firebase_admin import messaging


logger = logging.getLogger(__name__)


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


def _cart_item_price(item):
    """Единая цена позиции корзины для subtotal и OrderItem."""
    if item.variant_id:
        return item.variant.price

    first_variant = item.product.variants.filter(is_available=True).first()
    if first_variant:
        return first_variant.price

    return item.product.price or Decimal('0')


def _refund_order_bonus(order):
    """Возврат списанных бонусов. Вызывается только внутри transaction.atomic."""
    if not order.bonus_used or not order.user_id:
        return

    user = User.objects.select_for_update().get(pk=order.user_id)
    User.objects.filter(pk=user.pk).update(
        bonus_points=F('bonus_points') + order.bonus_used
    )


def _award_bonus_for_delivery(order):
    """Начисление бонусов за доставленный заказ."""
    if not order.user_id:
        return

    site = SiteSettings.get_settings()
    if not site.bonus_enabled:
        return

    earned_bonus = int(
        order.total_amount * Decimal(str(site.bonus_rate)) / Decimal('100')
    )
    if earned_bonus <= 0:
        return

    user = User.objects.select_for_update().get(pk=order.user_id)
    User.objects.filter(pk=user.pk).update(
        bonus_points=F('bonus_points') + earned_bonus
    )


def _notify_status_change(order, new_status):
    if not order.user or not order.user.fcm_token:
        return

    send_push_notification(
        order.user.fcm_token,
        f"Статус заказа #{order.order_number}",
        f"Ваш заказ теперь: {dict(Order.STATUS_CHOICES).get(new_status, new_status)}",
    )


def _send_order_email(order_id):
    """Отправка email после commit. Ошибки не должны ломать заказ."""
    try:
        from notifications.task import send_order_notification

        send_order_notification(order_id)
    except Exception:
        logger.exception(
            'Order email notification failed for order %s',
            order_id,
        )


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
            product = Product.objects.get(id=product_id, is_archived=False)
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
            product = Product.objects.get(id=product_id, is_archived=False)
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
    permission_classes = (permissions.AllowAny,)
    @transaction.atomic
    def post(self, request):
        serializer = CreateOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data

        is_authenticated = request.user.is_authenticated
        if is_authenticated:
            try:
                cart = Cart.objects.select_for_update().get(user=request.user)
            except Cart.DoesNotExist:
                return Response(
                    {'error': 'Корзина пуста'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user = User.objects.select_for_update().get(pk=request.user.pk)
        else:
            session_id = request.COOKIES.get('guest_session_id')
            if not session_id:
                return Response(
                    {'error': 'Корзина пуста'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            cart = Cart.objects.select_for_update().filter(
                session_id=session_id
            ).first()
            user = None

        if not cart:
            return Response(
                {'error': 'Корзина пуста'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart_items = list(cart.items.select_related('product', 'variant'))
        if not cart_items:
            return Response(
                {'error': 'Корзина пуста'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        site = SiteSettings.get_settings()

        priced_items = [(item, _cart_item_price(item)) for item in cart_items]
        subtotal = sum(
            (price * item.quantity for item, price in priced_items),
            Decimal('0'),
        )

        delivery_type = data.get('delivery_type', 'delivery')
        if delivery_type == 'pickup' or subtotal >= site.delivery_free_threshold:
            delivery_cost = Decimal('0')
        else:
            delivery_cost = Decimal(site.delivery_base_cost)

        requested_bonus = data.get('bonus_used', 0) if user else 0
        if requested_bonus > subtotal:
            return Response(
                {'error': 'Бонусов больше, чем стоимость заказа'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user and site.bonus_enabled:
            max_bonus_by_percent = int(
                subtotal * Decimal(site.bonus_max_percent) / Decimal('100')
            )
            bonus_used = max(
                0,
                min(requested_bonus, user.bonus_points, max_bonus_by_percent),
            )
        else:
            bonus_used = 0

        total = subtotal + delivery_cost - Decimal(bonus_used)
        if total < 0:
            return Response(
                {'error': 'Итоговая сумма не может быть отрицательной'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if bonus_used and user:
            User.objects.filter(pk=user.pk).update(
                bonus_points=F('bonus_points') - bonus_used
            )

        customer_name = (data.get('full_name') or '').strip()
        if not customer_name and user:
            customer_name = user.full_name or user.username

        customer_phone = (data.get('phone') or '').strip()
        if not customer_phone and user:
            customer_phone = user.phone or ''

        customer_email = (data.get('email') or '').strip()
        if not customer_email and user:
            customer_email = user.email or ''

        order_number = f"NVK-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        order = Order.objects.create(
            user=user,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=customer_email or None,
            order_number=order_number,
            delivery_address=data.get('delivery_address', ''),
            delivery_date=data.get('delivery_date'),
            delivery_time_from=data.get('delivery_time_from'),
            delivery_time_to=data.get('delivery_time_to'),
            comment=data.get('comment', ''),
            subtotal=subtotal,
            delivery_cost=delivery_cost,
            discount=0,
            bonus_used=bonus_used,
            total_amount=total,
            payment_method=data['payment_method'],
            status='new',
            delivery_type=delivery_type,
            pickup_time=data.get('pickup_time'),
            pickup_date=data.get('pickup_date'),
            persons_count=data.get('persons_count', 1),
            cutlery_count=data.get('cutlery_count', 2),
        )
        
        for item, price in priced_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                variant=item.variant,
                quantity=item.quantity,
                price_at_order=price,
            )
        
        cart.items.all().delete()

        transaction.on_commit(lambda: _send_order_email(order.id))

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

    @transaction.atomic
    def post(self, request, order_id):
        try:
            order = Order.objects.select_for_update().get(
                id=order_id,
                user=request.user,
            )
        except Order.DoesNotExist:
            return Response(
                {'error': 'Заказ не найден'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if order.status not in ('new', 'confirmed'):
            return Response(
                {'error': 'Заказ нельзя отменить (уже в обработке или доставлен)'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = order.status
        order.status = 'cancelled'
        order.save(update_fields=['status'])
        _refund_order_bonus(order)

        OrderStatusHistory.objects.create(
            order=order,
            from_status=old_status,
            to_status='cancelled',
            changed_by=request.user,
        )

        return Response(OrderSerializer(order).data)

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

    @transaction.atomic
    def put(self, request, order_id):
        if request.user.role != 'admin':
            return Response(
                {'error': 'Только администраторы могут изменять статус заказа'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            order = Order.objects.select_for_update().get(id=order_id)
        except Order.DoesNotExist:
            return Response(
                {'error': 'Заказ не найден'},
                status=status.HTTP_404_NOT_FOUND,
            )

        new_status = request.data.get('status')
        if new_status not in dict(Order.STATUS_CHOICES):
            return Response(
                {
                    'error': (
                        'Недопустимый статус. Допустимые: '
                        + ', '.join(dict(Order.STATUS_CHOICES).keys())
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        allowed = Order.ALLOWED_TRANSITIONS.get(order.status, set())
        if new_status not in allowed:
            return Response(
                {'error': f'Переход {order.status} -> {new_status} запрещён'},
                status=status.HTTP_409_CONFLICT,
            )

        if (
            new_status == 'delivered'
            and order.payment_method == 'online'
            and order.payment_status != 'paid'
        ):
            return Response(
                {'error': 'Нельзя доставить неоплаченный онлайн-заказ'},
                status=status.HTTP_409_CONFLICT,
            )

        old_status = order.status
        order.status = new_status
        order.save(update_fields=['status'])

        OrderStatusHistory.objects.create(
            order=order,
            from_status=old_status,
            to_status=new_status,
            changed_by=request.user,
        )

        if new_status == 'cancelled':
            _refund_order_bonus(order)

        if new_status == 'delivered':
            _award_bonus_for_delivery(order)

        transaction.on_commit(
            lambda: _notify_status_change(order, new_status)
        )

        return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)
