from decimal import Decimal

import pytest
from django.core.management import call_command

from orders.models import Cart, CartItem, Order, OrderStatusHistory
from products.models import Category, Favorite, Product, Review
from users.models import User


@pytest.mark.django_db
def test_merge_duplicate_users_dry_run_and_commit():
    primary = User.objects.create_user(
        username='primary-user',
        password='password-12345',
        phone='+79995550001',
        full_name='Основной',
        role='client',
        bonus_points=10,
    )
    duplicate = User.objects.create_user(
        username='duplicate-user',
        password='password-12345',
        phone='89995550001',
        full_name='Дубликат',
        role='client',
        bonus_points=5,
    )

    category = Category.objects.create(name='Роллы', slug='rolls')
    product = Product.objects.create(
        name='Филадельфия',
        category=category,
        price=Decimal('499.00'),
        weight=250,
    )

    order = Order.objects.create(
        user=duplicate,
        order_number='MERGE-TEST-001',
        delivery_address='Адрес',
        subtotal=Decimal('499.00'),
        total_amount=Decimal('499.00'),
        payment_method='cash',
    )
    OrderStatusHistory.objects.create(
        order=order,
        from_status='new',
        to_status='confirmed',
        changed_by=duplicate,
    )

    primary_cart = Cart.objects.create(user=primary)
    duplicate_cart = Cart.objects.create(user=duplicate)
    CartItem.objects.create(cart=primary_cart, product=product, quantity=1)
    CartItem.objects.create(cart=duplicate_cart, product=product, quantity=2)

    Favorite.objects.create(user=duplicate, product=product)
    Review.objects.create(
        user=duplicate,
        product=product,
        rating=5,
        text='Отзыв дубликата',
    )

    call_command(
        'merge_duplicate_users',
        '--primary', primary.id,
        '--duplicate', duplicate.id,
    )
    assert User.objects.filter(pk=duplicate.id).exists()
    order.refresh_from_db()
    assert order.user_id == duplicate.id

    call_command(
        'merge_duplicate_users',
        '--primary', primary.id,
        '--duplicate', duplicate.id,
        '--commit',
    )

    assert not User.objects.filter(pk=duplicate.id).exists()
    primary.refresh_from_db()
    assert primary.phone == '79995550001'
    assert primary.username == '79995550001'
    assert primary.bonus_points == 10
    assert primary.full_name == 'Основной'

    order.refresh_from_db()
    assert order.user_id == primary.id
    assert OrderStatusHistory.objects.get(order=order).changed_by_id == primary.id

    primary_cart.refresh_from_db()
    assert primary_cart.items.get(product=product).quantity == 3
    assert Favorite.objects.filter(user=primary, product=product).exists()
    assert Review.objects.filter(user=primary, product=product).exists()
