# tests/test_products.py
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from products.models import Category, Product


@pytest.mark.django_db
class TestProductAPI:
    
    def setup_method(self):
        self.client = APIClient()
        
        # Создаём категорию
        self.category = Category.objects.create(
            name='Роллы',
            slug='rolls'
        )
        
        # Создаём товар
        self.product = Product.objects.create(
            name='Филадельфия классическая',
            category=self.category,
            price=499.00,
            weight=250,
            ingredients='Лосось, сливочный сыр, огурец'
        )
    
    def test_product_list(self):
        """Тест получения списка товаров"""
        url = reverse('products:product-list')
        response = self.client.get(url)
        
        assert response.status_code == 200
        assert len(response.data) >= 1
        assert response.data[0]['name'] == 'Филадельфия классическая'
    
    def test_product_detail(self):
        """Тест получения деталей товара"""
        url = reverse('products:product-detail', kwargs={'pk': self.product.id})
        response = self.client.get(url)
        
        assert response.status_code == 200
        assert response.data['name'] == 'Филадельфия классическая'