# products/admin.py
from django.contrib import admin
from .models import Category, Product, ProductVariant, Review


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'sort_order')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


class ProductVariantInline(admin.TabularInline):
    """Вариации внутри карточки товара (inline)"""
    model = ProductVariant
    extra = 1
    fields = ('name', 'price', 'old_price', 'weight', 'is_available')
    ordering = ('price',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'get_min_price', 'is_hit', 'is_new')
    list_filter = ('category', 'is_hit', 'is_new')
    search_fields = ('name', 'description', 'ingredients')
    prepopulated_fields = {}
    inlines = [ProductVariantInline]
    
    # ✅ ТОЛЬКО FIELDSETS — ОН АВТОМАТИЧЕСКИ ВКЛЮЧАЕТ ВСЕ ПОЛЯ
    fieldsets = (
        (None, {
            'fields': ('name', 'category', 'description', 'ingredients')
        }),
        ('Цена и вес (для товаров без вариаций)', {
            'fields': ('price', 'weight')  # ← ЭТИ ПОЛЯ БУДУТ В ФОРМЕ
        }),
        ('Изображение', {
            'fields': ('image', 'image_url')
        }),
        ('Маркировка', {
            'fields': ('is_hit', 'is_new')
        }),
    )

    def get_min_price(self, obj):
        """Отображает минимальную цену среди вариаций или цену товара"""
        if not obj:
            return "—"
        variants = obj.variants.filter(is_available=True).order_by('price')
        if variants.exists():
            return f"{variants.first().price} ₽"
        if obj.price:
            return f"{obj.price} ₽"
        return "—"
    get_min_price.short_description = "Цена (от)"

    # ✅ ПЕРЕОПРЕДЕЛЯЕМ get_form, чтобы поля были обязательными только для товаров без вариаций
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.variants.exists():
            # Если есть вариации — делаем price и weight необязательными
            form.base_fields['price'].required = False
            form.base_fields['weight'].required = False
        else:
            # Если вариаций нет — делаем price обязательным
            form.base_fields['price'].required = True
            form.base_fields['weight'].required = False
        return form


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'name', 'price', 'old_price', 'weight', 'is_available')
    list_filter = ('product__category', 'is_available')
    search_fields = ('product__name', 'name')
    ordering = ('product', 'price')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'user', 'rating', 'created_at', 'is_approved')
    list_filter = ('rating', 'is_approved', 'created_at')
    search_fields = ('product__name', 'user__username', 'text')
    actions = ['approve_reviews', 'disapprove_reviews']

    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
    approve_reviews.short_description = "Одобрить выбранные отзывы"

    def disapprove_reviews(self, request, queryset):
        queryset.update(is_approved=False)
    disapprove_reviews.short_description = "Скрыть выбранные отзывы"