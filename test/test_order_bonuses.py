# tests/test_order_bonuses.py
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from core.models import SiteSettings
from orders.models import Cart, CartItem, Order
from products.models import Category, Product
from users.models import User


@pytest.mark.django_db
class TestOrderBonuses:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='bonus-user',
            password='bonus-password-123',
            phone='+79990000200',
            bonus_points=200,
            role='client',
        )
        self.category = Category.objects.create(name='Роллы', slug='rolls')
        self.product = Product.objects.create(
            name='Филадельфия',
            category=self.category,
            price=Decimal('1000.00'),
            weight=250,
        )
        self.cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=1)

        self.site = SiteSettings.get_settings()
        self.site.bonus_enabled = True
        self.site.bonus_max_percent = 100
        self.site.delivery_base_cost = 150
        self.site.delivery_free_threshold = 800
        self.site.save()
        self.client.force_authenticate(user=self.user)

    def _set_balance(self, value):
        User.objects.filter(pk=self.user.pk).update(bonus_points=value)
        self.user.refresh_from_db()

    def _payload(self, **overrides):
        payload = {
            'payment_method': 'cash',
            'delivery_type': 'pickup',
            'delivery_address': 'Тестовый адрес',
            'bonus_used': 0,
        }
        payload.update(overrides)
        return payload

    def _create_order(self, **overrides):
        return self.client.post(
            reverse('orders:create-order'),
            self._payload(**overrides),
            format='json',
        )

    def test_bonus_is_capped_by_balance(self):
        self._set_balance(200)

        response = self._create_order(bonus_used=500)

        assert response.status_code == 201, response.data
        order = Order.objects.get(user=self.user)
        assert order.bonus_used == 200
        assert order.total_amount == Decimal('800.00')

        self.user.refresh_from_db()
        assert self.user.bonus_points == 0
        assert CartItem.objects.filter(cart=self.cart).exists() is False

    def test_bonus_is_capped_by_site_percent(self):
        self._set_balance(1000)
        self.site.bonus_max_percent = 30
        self.site.save(update_fields=['bonus_max_percent'])

        response = self._create_order(bonus_used=500)

        assert response.status_code == 201, response.data
        order = Order.objects.get(user=self.user)
        assert order.bonus_used == 300
        assert order.total_amount == Decimal('700.00')

        self.user.refresh_from_db()
        assert self.user.bonus_points == 700

    def test_bonus_greater_than_order_total_is_rejected(self):
        self._set_balance(5000)

        response = self._create_order(bonus_used=1500)

        assert response.status_code == 400
        assert Order.objects.count() == 0
        self.user.refresh_from_db()
        assert self.user.bonus_points == 5000
        assert CartItem.objects.filter(cart=self.cart).exists() is True

    def test_cancel_returns_bonus_once(self):
        self._set_balance(800)
        order = Order.objects.create(
            user=self.user,
            order_number='NVK-BONUS-CANCEL',
            delivery_address='Тестовый адрес',
            subtotal=Decimal('1000.00'),
            total_amount=Decimal('800.00'),
            bonus_used=200,
            payment_method='cash',
        )

        first = self.client.post(
            reverse('orders:cancel-order', kwargs={'order_id': order.id}),
        )
        assert first.status_code == 200, first.data

        order.refresh_from_db()
        self.user.refresh_from_db()
        assert order.status == 'cancelled'
        assert self.user.bonus_points == 1000

        second = self.client.post(
            reverse('orders:cancel-order', kwargs={'order_id': order.id}),
        )
        assert second.status_code == 400

        self.user.refresh_from_db()
        assert self.user.bonus_points == 1000

    def test_repeated_spend_does_not_make_balance_negative(self):
        self._set_balance(100)

        first = self._create_order(bonus_used=100)
        assert first.status_code == 201, first.data
        self.user.refresh_from_db()
        assert self.user.bonus_points == 0

        # Пополняем корзину снова и повторяем списание.
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=1)
        second = self._create_order(bonus_used=100)

        assert second.status_code == 201, second.data
        latest = Order.objects.filter(user=self.user).order_by('-id').first()
        assert latest.bonus_used == 0
        self.user.refresh_from_db()
        assert self.user.bonus_points == 0

    def test_delivery_cost_comes_from_site_settings(self):
        self._set_balance(0)
        self.site.delivery_base_cost = 200
        self.site.delivery_free_threshold = 500
        self.site.save(update_fields=['delivery_base_cost', 'delivery_free_threshold'])

        self.product.price = Decimal('400.00')
        self.product.save(update_fields=['price'])

        response = self._create_order(
            delivery_type='delivery',
            bonus_used=0,
        )

        assert response.status_code == 201, response.data
        order = Order.objects.get(user=self.user)
        assert order.delivery_cost == Decimal('200.00')
        assert order.total_amount == Decimal('600.00')

    def test_bonus_disabled_means_no_spending(self):
        self._set_balance(1000)
        self.site.bonus_enabled = False
        self.site.save(update_fields=['bonus_enabled'])

        response = self._create_order(bonus_used=500)

        assert response.status_code == 201, response.data
        order = Order.objects.get(user=self.user)
        assert order.bonus_used == 0
        assert order.total_amount == Decimal('1000.00')
        self.user.refresh_from_db()
        assert self.user.bonus_points == 1000
