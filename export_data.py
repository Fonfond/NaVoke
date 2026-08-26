import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'navoke_backend.settings')
django.setup()

from products.models import Product, Category, ProductVariant, LunchMenu

# Экспортируем данные в формате Django fixtures
data = []

# Категории
for obj in Category.objects.all():
    data.append({
        'model': 'products.category',
        'pk': obj.pk,
        'fields': {
            'name': obj.name,
            'slug': obj.slug,
            'image_url': obj.image_url,
            'sort_order': obj.sort_order,
        }
    })

# Товары - исправляем пустые цены
for obj in Product.objects.all():
    price = obj.price if obj.price else 0  # ✅ Если цена пустая - ставим 0
    data.append({
        'model': 'products.product',
        'pk': obj.pk,
        'fields': {
            'name': obj.name,
            'category': obj.category_id,
            'description': obj.description,
            'ingredients': obj.ingredients,
            'image': str(obj.image) if obj.image else '',
            'image_url': obj.image_url,
            'is_hit': obj.is_hit,
            'is_new': obj.is_new,
            'created_at': obj.created_at.isoformat(),
            'has_variants': obj.has_variants,
            'price': str(price),  # ✅ Исправлено
            'weight': obj.weight or 0,
        }
    })

# Вариации - исправляем пустые цены
for obj in ProductVariant.objects.all():
    price = obj.price if obj.price else 0  # ✅ Если цена пустая - ставим 0
    old_price = obj.old_price if obj.old_price else 0  # ✅ Если старая цена пустая - ставим 0
    data.append({
        'model': 'products.productvariant',
        'pk': obj.pk,
        'fields': {
            'product': obj.product_id,
            'name': obj.name,
            'price': str(price),  # ✅ Исправлено
            'old_price': str(old_price),  # ✅ Исправлено
            'weight': obj.weight or 0,
            'is_available': obj.is_available,
        }
    })

# Меню бизнес-ланча
for obj in LunchMenu.objects.all():
    data.append({
        'model': 'products.lunchmenu',
        'pk': obj.pk,
        'fields': {
            'date': obj.date.isoformat(),
            'title': obj.title,
            'items': obj.items,
            'is_active': obj.is_active,
            'created_at': obj.created_at.isoformat(),
        }
    })

with open('db_export.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✅ Данные экспортированы в db_export.json")
print(f"📦 Категорий: {len(Category.objects.all())}")
print(f"📦 Товаров: {len(Product.objects.all())}")
print(f"📦 Вариаций: {len(ProductVariant.objects.all())}")