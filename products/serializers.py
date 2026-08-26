# products/serializers.py
from rest_framework import serializers
from .models import Category, Product, LunchMenu, ProductVariant, Favorite, Review
from django.conf import settings


class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ('id', 'name', 'price', 'old_price', 'weight', 'is_available')


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug', 'image_url', 'sort_order')


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.full_name')
    user_avatar = serializers.SerializerMethodField()
    
    class Meta:
        model = Review
        fields = ('id', 'product', 'user', 'user_name', 'user_avatar', 'rating', 'text', 'created_at')
        read_only_fields = ('id', 'product', 'user', 'created_at')
    
    def get_user_avatar(self, obj):
        if obj.user.avatar:
            return f"{settings.MEDIA_URL}{obj.user.avatar}"
        return ''


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')
    category_slug = serializers.ReadOnlyField(source='category.slug')
    image_url = serializers.SerializerMethodField()
    variants = ProductVariantSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()
    min_price = serializers.SerializerMethodField()
    has_variants = serializers.SerializerMethodField()
    
    # ✅ ОДНО ПОЛЕ price — оно будет возвращать правильную цену для всех случаев
    price = serializers.SerializerMethodField()
    weight = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'category', 'category_name', 'category_slug',
            'description', 'ingredients', 'image', 'image_url',
            'is_hit', 'is_new', 'created_at',
            'variants', 'min_price', 'has_variants',
            'reviews', 'average_rating',
            'price', 'weight'
        )
        read_only_fields = ('created_at',)

    def get_image_url(self, obj):
        if obj.image:
            return f"{settings.MEDIA_URL}{obj.image}"
        return obj.image_url or ''

    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        if not reviews:
            return 0
        return round(sum(r.rating for r in reviews) / len(reviews), 1)

    def get_min_price(self, obj):
        variants = obj.variants.filter(is_available=True)
        if not variants:
            return None
        return variants.order_by('price').first().price
    
    def get_price(self, obj):
        """Возвращает цену для всех типов товаров"""
        variants = obj.variants.filter(is_available=True)
        if variants.exists():
            return variants.order_by('price').first().price
        # Если вариаций нет — возвращаем цену из поля price в БД
        return obj.price
    
    def get_weight(self, obj):
        """Возвращает вес для всех типов товаров"""
        variants = obj.variants.filter(is_available=True)
        if variants.exists():
            return variants.order_by('price').first().weight
        return obj.weight or 0

    def get_has_variants(self, obj):
        return obj.variants.filter(is_available=True).exists()

class LunchMenuSerializer(serializers.ModelSerializer):
    class Meta:
        model = LunchMenu
        fields = '__all__'

class FavoriteSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    product_price = serializers.SerializerMethodField()
    product_image = serializers.SerializerMethodField()
    
    class Meta:
        model = Favorite
        fields = ('id', 'product', 'product_name', 'product_price', 'product_image', 'created_at')
    
    def get_product_price(self, obj):
        variants = obj.product.variants.filter(is_available=True)
        if variants:
            return variants.order_by('price').first().price
        return obj.product.price or 0
    
    def get_product_image(self, obj):
        if obj.product.image:
            return f"{settings.MEDIA_URL}{obj.product.image}"
        return obj.product.image_url or ''