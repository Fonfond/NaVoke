# tests/test_product_delete.py
from decimal import Decimal
from uuid import uuid4

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from orders.models import Cart, CartItem, Order, OrderItem
from products.models import Category, Product
from users.models import User


@pytest.mark.django_db
class TestProductDelete:
    def setup_method(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='admin-delete',
            password='admin-password-123',
            phone='+79990000002',
            role='admin',
        )
        self.category = Category.objects.create(name='Роллы', slug='rolls')
        self.product = Product.objects.create(
            name='Филадельфия',
            category=self.category,
            price=Decimal('100.00'),
            weight=250,
        )
        self.client.force_authenticate(user=self.admin)

    def _create_order_item(self, product=None):
        order = Order.objects.create(
            user=self.admin,
            order_number=f'TEST-{uuid4().hex[:10].upper()}',
            delivery_address='Тестовый адрес',
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            payment_method='cash',
        )
        return OrderItem.objects.create(
            order=order,
            product=product or self.product,
            quantity=1,
            price_at_order=Decimal('100.00'),
        )

    def test_product_with_order_items_is_archived_not_deleted(self):
        order_item = self._create_order_item()
        client = User.objects.create_user(
            username='client-delete',
            password='client-password-123',
            phone='+79990000003',
            role='client',
        )
        cart = Cart.objects.create(user=client)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)

        url = reverse('products:product-delete', kwargs={'pk': self.product.id})
        response = self.client.delete(url)

        assert response.status_code == 200, response.data
        assert response.data['archived'] is True
        assert 'истории заказов' in response.data['message']

        self.product.refresh_from_db()
        assert self.product.is_archived is True
        assert Product.objects.filter(pk=self.product.pk).exists() is True
        assert OrderItem.objects.filter(pk=order_item.pk).exists() is True
        # товар убран из корзины, но история заказа сохранена
        assert CartItem.objects.filter(product=self.product).exists() is False

        list_response = self.client.get(reverse('products:product-list'))
        assert list_response.status_code == 200
        ids = [item['id'] for item in list_response.data['results']]
        assert self.product.id not in ids

        detail_url = reverse('products:product-detail', kwargs={'pk': self.product.id})
        detail_response = self.client.get(detail_url)
        assert detail_response.status_code == 404

    def test_product_without_order_items_is_deleted(self):
        product = Product.objects.create(
            name='Удаляемый товар',
            category=self.category,
            price=Decimal('200.00'),
            weight=100,
        )
        url = reverse('products:product-delete', kwargs={'pk': product.id})
        response = self.client.delete(url)

        assert response.status_code == 200, response.data
        assert response.data['archived'] is False
        assert Product.objects.filter(pk=product.pk).exists() is False

    def test_non_admin_cannot_delete_product(self):
        client_user = User.objects.create_user(
            username='client-no-delete',
            password='client-password-123',
            phone='+79990000004',
            role='client',
        )
        self.client.force_authenticate(user=client_user)
        url = reverse('products:product-delete', kwargs={'pk': self.product.id})
        response = self.client.delete(url)

        assert response.status_code == 403
        assert Product.objects.filter(pk=self.product.pk).exists() is True

    def test_archived_product_is_hidden_from_live_search(self):
        self.product.is_archived = True
        self.product.save(update_fields=['is_archived'])

        response = self.client.get(
            reverse('products:live-search'),
            {'q': 'Филадельфия'},
        )

        assert response.status_code == 200
        assert response.data == []

    def test_archived_product_cannot_be_added_to_cart(self):
        self.product.is_archived = True
        self.product.save(update_fields=['is_archived'])
        client_user = User.objects.create_user(
            username='client-archived',
            password='client-password-123',
            phone='+79990000005',
            role='client',
        )
        self.client.force_authenticate(user=client_user)

        response = self.client.post(
            reverse('orders:add-to-cart'),
            {'product_id': self.product.id, 'quantity': 1},
            format='json',
        )

        assert response.status_code == 404
