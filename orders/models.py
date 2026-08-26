# orders/models.py
from django.db import models
from users.models import User
from products.models import Product, ProductVariant


class Cart(models.Model):
    """Модель корзины пользователя"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='cart',
        null=True,
        blank=True
    )
    session_id = models.CharField(
        max_length=100, 
        null=True, 
        blank=True, 
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'carts'

    def __str__(self):
        if self.user:
            return f"Корзина {self.user.username}"
        return f"Корзина {self.session_id[:8] if self.session_id else 'guest'}"

    @property
    def total(self):
        return sum(item.total for item in self.items.all())


class CartItem(models.Model):
    """Товар в корзине"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    variant = models.ForeignKey(
        ProductVariant, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = 'cart_items'
        unique_together = ('cart', 'product', 'variant')

    def __str__(self):
        if self.variant:
            return f"{self.quantity}x {self.product.name} - {self.variant.name}"
        return f"{self.quantity}x {self.product.name}"

    @property
    def total(self):
        # 1. Если есть вариация — берём цену из вариации
        if self.variant:
            return self.variant.price * self.quantity
        
        # 2. Если вариации нет, но у товара есть вариации в БД — берём первую доступную
        first_variant = self.product.variants.filter(is_available=True).first()
        if first_variant:
            return first_variant.price * self.quantity
        
        # 3. ✅ ЕСЛИ ВАРИАЦИЙ НЕТ ВООБЩЕ — БЕРЁМ ЦЕНУ ИЗ ПОЛЯ price В ТОВАРЕ
        if self.product.price:
            return self.product.price * self.quantity
        
        # 4. Если ничего нет — возвращаем 0
        return 0


class Order(models.Model):
    """Модель заказа"""
    STATUS_CHOICES = (
        ('new', 'Новый'),
        ('confirmed', 'Подтверждён'),
        ('cooking', 'Готовится'),
        ('ready', 'Готов к выдаче'),
        ('delivering', 'В доставке'),
        ('delivered', 'Доставлен'),
        ('cancelled', 'Отменён'),
    )

    DELIVERY_TYPE_CHOICES = (
        ('delivery', 'Доставка'),
        ('pickup', 'Самовывоз'),
    )

    PAYMENT_METHODS = (
        ('online', 'Онлайн картой'),
        ('cash', 'Наличными курьеру'),
    )

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='orders')
    courier = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='deliveries')
    order_number = models.CharField(max_length=20, unique=True)
    order_date = models.DateTimeField(auto_now_add=True)

    delivery_address = models.TextField()
    delivery_date = models.DateField(null=True, blank=True)
    delivery_time_from = models.TimeField(null=True, blank=True)
    delivery_time_to = models.TimeField(null=True, blank=True)
    comment = models.TextField(blank=True)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    bonus_used = models.IntegerField(default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    payment_status = models.CharField(max_length=20, default='pending')
    
    delivery_type = models.CharField(
        max_length=20, 
        choices=DELIVERY_TYPE_CHOICES, 
        default='delivery'
    )
    pickup_time = models.TimeField(null=True, blank=True, help_text='Желаемое время самовывоза')
    pickup_date = models.DateField(null=True, blank=True, help_text='Желаемая дата самовывоза')

    class Meta:
        db_table = 'orders'
        ordering = ['-order_date']

    def __str__(self):
        return f"Заказ {self.order_number} - {self.user.username}"
    delivery_lat = models.FloatField(null=True, blank=True, verbose_name='Широта адреса')
    delivery_lng = models.FloatField(null=True, blank=True, verbose_name='Долгота адреса')


class OrderItem(models.Model):
    """Товар в заказе"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name='Вариация'
    )
    quantity = models.PositiveIntegerField()
    price_at_order = models.DecimalField(max_digits=10, decimal_places=2)
    custom_ingredients = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'order_items'
        # unique_together = ('order', 'product')  # ← УБРАЛИ (или оставь, если нужно)
        

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"