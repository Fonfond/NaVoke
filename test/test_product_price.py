# tests/test_product_price.py
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from products.models import Category, Product
from users.models import User


@pytest.mark.django_db
class TestProductPriceWrite:
    def setup_method(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='admin',
            password='admin-password-123',
            phone='+79990000001',
            role='admin',
        )
        self.category = Category.objects.create(name='Роллы', slug='rolls')
        self.client.force_authenticate(user=self.admin)

    def _payload(self, **overrides):
        payload = {
            'name': 'Филадельфия',
            'category': self.category.id,
            'description': 'Описание',
            'ingredients': 'Лосось, сыр',
            'price': '499.00',
            'weight': 250,
            'has_variants': False,
        }
        payload.update(overrides)
        return payload

    def test_create_product_persists_price(self):
        url = reverse('products:product-list')
        response = self.client.post(url, self._payload(), format='json')

        assert response.status_code == 201, response.data
        product = Product.objects.get(pk=response.data['id'])
        assert product.price == Decimal('499.00')
        assert product.weight == 250
        assert product.has_variants is False
        assert Decimal(str(response.data['price'])) == Decimal('499.00')

    def test_create_product_without_price_is_rejected(self):
        url = reverse('products:product-list')
        payload = self._payload(price=None)
        response = self.client.post(url, payload, format='json')

        assert response.status_code == 400
        assert 'price' in response.data
        assert not Product.objects.filter(name='Филадельфия').exists()

    def test_update_product_price(self):
        product = Product.objects.create(
            name='Калифорния',
            category=self.category,
            price=Decimal('399.00'),
            weight=200,
        )
        url = reverse('products:product-update', kwargs={'pk': product.id})
        payload = self._payload(name='Калифорния', price='599.00', weight=220)
        response = self.client.put(url, payload, format='json')

        assert response.status_code == 200, response.data
        product.refresh_from_db()
        assert product.price == Decimal('599.00')
        assert product.weight == 220
        assert Decimal(str(response.data['price'])) == Decimal('599.00')

    def test_product_with_variants_can_have_no_base_price(self):
        url = reverse('products:product-list')
        response = self.client.post(
            url,
            self._payload(name='Сет с вариациями', price=None, has_variants=True),
            format='json',
        )

        assert response.status_code == 201, response.data
        product = Product.objects.get(pk=response.data['id'])
        assert product.price is None
        assert response.data['has_variants'] is True

        variant_url = reverse('products:variant-create', kwargs={'product_id': product.id})
        variant_response = self.client.post(
            variant_url,
            {'name': '30 см', 'price': '700.00', 'weight': 300, 'is_available': True},
            format='json',
        )
        assert variant_response.status_code == 201, variant_response.data

        detail_url = reverse('products:product-detail', kwargs={'pk': product.id})
        detail = self.client.get(detail_url)
        assert detail.status_code == 200
        assert Decimal(str(detail.data['price'])) == Decimal('700.00')

    def test_image_url_is_writable(self):
        url = reverse('products:product-list')
        response = self.client.post(
            url,
            self._payload(image_url='https://example.com/product.jpg'),
            format='json',
        )

        assert response.status_code == 201, response.data
        product = Product.objects.get(pk=response.data['id'])
        assert product.image_url == 'https://example.com/product.jpg'
        assert response.data['image_url'] == 'https://example.com/product.jpg'
