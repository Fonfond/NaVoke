# products/models.py
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
    image_url = models.URLField(null=True, blank=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = 'categories'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class Product(models.Model):
    """Родительский товар (например, Пицца Маргарита)"""
    name = models.CharField(max_length=150)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    description = models.TextField(blank=True)
    ingredients = models.TextField(blank=True)
    image = models.ImageField(
        upload_to='products/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name='Изображение'
    )
    image_url = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name='Ссылка на изображение'
    )
    is_hit = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    has_variants = models.BooleanField(default=False, verbose_name='Есть вариации?')

    # ✅ ДОБАВЛЕНЫ ПОЛЯ ДЛЯ ТОВАРОВ БЕЗ ВАРИАЦИЙ
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name='Цена (для товаров без вариаций)'
    )
    weight = models.IntegerField(
        null=True, 
        blank=True,
        default=0,
        verbose_name='Вес (для товаров без вариаций)'
    )

    class Meta:
        db_table = 'products'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class ProductVariant(models.Model):
    """Вариация товара (например, Маргарита 30 см, Маргарита 40 см)"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=50, blank=True, help_text='Например: 30 см, 40 см, большой')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    old_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    weight = models.IntegerField(help_text='Вес в граммах', default=0)
    is_available = models.BooleanField(default=True)

    class Meta:
        db_table = 'product_variants'
        ordering = ['price']
        unique_together = ('product', 'name')

    def __str__(self):
        return f"{self.product.name} - {self.name or 'Стандарт'} ({self.price} ₽)"


class Favorite(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='favorites')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'favorites'
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user.username} → {self.product.name}"

class LunchMenu(models.Model):
    """Меню бизнес-ланча на день"""
    date = models.DateField(unique=True, verbose_name='Дата')
    title = models.CharField(max_length=200, default='Бизнес-ланч', verbose_name='Заголовок')
    items = models.JSONField(default=list, verbose_name='Позиции меню')
    is_active = models.BooleanField(default=True, verbose_name='Активно')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lunch_menus'
        ordering = ['-date']

    def __str__(self):
        return f"Меню на {self.date}"

class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(
        choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')],
        default=5
    )
    text = models.TextField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=True)

    class Meta:
        db_table = 'reviews'
        ordering = ['-created_at']
        unique_together = ('product', 'user')

    def __str__(self):
        return f"Отзыв {self.user.username} на {self.product.name} — {self.rating}⭐"