# orders/serializers.py
from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem
from products.models import Product
from django.conf import settings


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    product_price = serializers.SerializerMethodField()
    product_image = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = ('id', 'product', 'product_name', 'product_price', 
                  'quantity', 'product_image', 'total')
    
    def get_total(self, obj):
        # Используем правильную цену из get_product_price
        return self.get_product_price(obj) * obj.quantity
    
    def get_product_price(self, obj):
        # 1. Если есть вариация — берём цену из вариации
        if obj.variant:
            return obj.variant.price
        
        # 2. Если вариации нет, но у товара есть вариации в БД — берём первую доступную
        first_variant = obj.product.variants.filter(is_available=True).first()
        if first_variant:
            return first_variant.price
        
        # 3. Если вариаций нет вообще — берём цену из самого товара (поле price)
        if obj.product.price:
            return obj.product.price
        
        # 4. Если ничего нет — возвращаем 0
        return 0
    
    def get_product_image(self, obj):
        if obj.product.image:
            return f"{settings.MEDIA_URL}{obj.product.image}"
        return obj.product.image_url or ''


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = ('id', 'user', 'items', 'total', 'items_count', 'created_at', 'updated_at')
    
    def get_total(self, obj):
        # ✅ ПРОСТОЙ И НАДЁЖНЫЙ СПОСОБ: суммируем через свойство модели
        return sum(item.total for item in obj.items.all())
    
    def get_items_count(self, obj):
        return obj.items.count()


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    product_image = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = ('id', 'product', 'product_name', 'product_image', 'quantity', 
                  'price_at_order', 'custom_ingredients')
    
    def get_product_image(self, obj):
        if obj.product.image:
            return f"{settings.MEDIA_URL}{obj.product.image}"
        return obj.product.image_url or ''


class CreateOrderSerializer(serializers.Serializer):
    delivery_address = serializers.CharField(max_length=500, required=False, allow_blank=True)
    delivery_date = serializers.DateField(required=False, allow_null=True)
    delivery_time_from = serializers.TimeField(required=False, allow_null=True)
    delivery_time_to = serializers.TimeField(required=False, allow_null=True)
    comment = serializers.CharField(required=False, allow_blank=True)
    payment_method = serializers.ChoiceField(choices=Order.PAYMENT_METHODS)
    bonus_used = serializers.IntegerField(default=0, min_value=0)
    delivery_type = serializers.ChoiceField(choices=Order.DELIVERY_TYPE_CHOICES, default='delivery')
    pickup_time = serializers.TimeField(required=False, allow_null=True)
    pickup_date = serializers.DateField(required=False, allow_null=True)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user_name = serializers.ReadOnlyField(source='user.full_name')
    status_display = serializers.ReadOnlyField(source='get_status_display')
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    
    class Meta:
        model = Order
        fields = (
            'id', 'order_number', 'user', 'user_name', 'courier',
            'order_date', 'delivery_address', 'delivery_date',
            'delivery_time_from', 'delivery_time_to', 'comment',
            'subtotal', 'delivery_cost', 'discount', 'total_amount',
            'bonus_used', 'status', 'status_display', 'payment_method',
            'payment_status', 'items',
            'delivery_type', 'pickup_time', 'pickup_date',
            'delivery_lat', 'delivery_lng', # ✅ Добавить сюда
            'full_name', 'phone', 'payment_method_display',
            'persons_count', 'cutlery_count',
        )
        read_only_fields = ('order_number', 'order_date', 'status', 'payment_status')
