from decimal import Decimal
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from products.models import Category, Product, ProductVariant
from users.models import User


@pytest.mark.django_db
class TestAdminProductApi:
    def setup_method(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='admin-panel',
            password='admin-password-123',
            phone='+79990000101',
            role='admin',
        )
        self.category = Category.objects.create(name='Роллы', slug='rolls')
        self.product = Product.objects.create(
            name='Филадельфия',
            category=self.category,
            price=Decimal('499.00'),
            weight=250,
            has_variants=False,
        )
        self.client.force_authenticate(user=self.admin)

    def _payload(self, **overrides):
        payload = {
            'name': self.product.name,
            'category': self.category.id,
            'description': 'Описание',
            'ingredients': 'Лосось, сыр',
            'is_hit': False,
            'is_new': False,
            'has_variants': False,
            'price': '499.00',
            'weight': 250,
        }
        payload.update(overrides)
        return payload

    def test_update_without_price_for_product_without_variants_is_400(self):
        url = reverse('products:product-update', kwargs={'pk': self.product.id})
        response = self.client.put(
            url,
            self._payload(price=None, weight=0),
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'price' in response.data

    def test_update_with_price_succeeds(self):
        url = reverse('products:product-update', kwargs={'pk': self.product.id})
        response = self.client.put(
            url,
            self._payload(price='599.00', weight=220),
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        self.product.refresh_from_db()
        assert self.product.price == Decimal('599.00')
        assert self.product.weight == 220

    def test_update_product_with_existing_variants_and_false_flag_allows_no_price(self):
        variant_product = Product.objects.create(
            name='Сет',
            category=self.category,
            price=None,
            weight=0,
            has_variants=False,
        )
        ProductVariant.objects.create(
            product=variant_product,
            name='Большой',
            price=Decimal('999.00'),
        )
        url = reverse(
            'products:product-update',
            kwargs={'pk': variant_product.id},
        )

        response = self.client.put(
            url,
            self._payload(
                name='Сет',
                price=None,
                weight=0,
                has_variants=False,
            ),
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        variant_product.refresh_from_db()
        assert variant_product.name == 'Сет'


@pytest.mark.django_db
class TestAdminVariantApi:
    def setup_method(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='admin-variant',
            password='admin-password-123',
            phone='+79990000102',
            role='admin',
        )
        self.category = Category.objects.create(name='Роллы', slug='rolls')
        self.product = Product.objects.create(
            name='Филадельфия',
            category=self.category,
            price=Decimal('499.00'),
            weight=250,
            has_variants=True,
        )
        self.other_product = Product.objects.create(
            name='Другой товар',
            category=self.category,
            price=Decimal('300.00'),
            weight=100,
            has_variants=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            name='Стандарт',
            price=Decimal('499.00'),
            weight=250,
        )
        self.client.force_authenticate(user=self.admin)

    def test_update_variant(self):
        url = reverse(
            'products:variant-detail',
            kwargs={'product_id': self.product.id, 'pk': self.variant.id},
        )
        response = self.client.put(
            url,
            {
                'name': 'Большой',
                'price': '699.00',
                'weight': 350,
                'is_available': True,
            },
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        self.variant.refresh_from_db()
        assert self.variant.name == 'Большой'
        assert self.variant.price == Decimal('699.00')
        assert self.variant.weight == 350

    def test_delete_variant(self):
        url = reverse(
            'products:variant-detail',
            kwargs={'product_id': self.product.id, 'pk': self.variant.id},
        )
        response = self.client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not ProductVariant.objects.filter(pk=self.variant.id).exists()

    def test_variant_from_other_product_is_404(self):
        url = reverse(
            'products:variant-detail',
            kwargs={'product_id': self.other_product.id, 'pk': self.variant.id},
        )
        response = self.client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert ProductVariant.objects.filter(pk=self.variant.id).exists()

    def test_non_admin_cannot_delete_variant(self):
        client = User.objects.create_user(
            username='client-variant',
            password='client-password-123',
            phone='+79990000103',
            role='client',
        )
        self.client.force_authenticate(user=client)
        url = reverse(
            'products:variant-detail',
            kwargs={'product_id': self.product.id, 'pk': self.variant.id},
        )

        response = self.client.delete(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert ProductVariant.objects.filter(pk=self.variant.id).exists()


@pytest.mark.django_db
def test_upload_product_image(settings):
    media_root = Path.cwd() / '.tmp' / 'test_media'
    media_root.mkdir(parents=True, exist_ok=True)
    settings.MEDIA_ROOT = str(media_root)
    client = APIClient()
    admin = User.objects.create_user(
        username='admin-image',
        password='admin-password-123',
        phone='+79990000104',
        role='admin',
    )
    category = Category.objects.create(name='Роллы', slug='rolls')
    product = Product.objects.create(
        name='Филадельфия',
        category=category,
        price=Decimal('499.00'),
        weight=250,
    )
    client.force_authenticate(user=admin)

    image = SimpleUploadedFile(
        'product.gif',
        b'GIF89a',
        content_type='image/gif',
    )
    url = reverse('products:upload-image', kwargs={'product_id': product.id})
    response = client.post(url, {'image': image}, format='multipart')

    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data['success'] is True
    assert response.data['image_url']
    product.refresh_from_db()
    assert product.image
