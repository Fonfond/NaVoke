# tests/test_cart.py
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from users.models import User
from products.models import Category, Product


@pytest.mark.django_db
class TestCartAPI:
    
    def setup_method(self):
        self.client = APIClient()
        
        # Создаём пользователя
        self.user = User.objects.create_user(
            username='testuser',
            password='12345678'
        )
        
        # Создаём категорию и товар
        self.category = Category.objects.create(name='Роллы', slug='rolls')
        self.product = Product.objects.create(
            name='Филадельфия классическая',
            category=self.category,
            price=499.00,
            weight=250,
            is_available=True
        )
    
    def test_add_to_cart(self):
        """Тест добавления товара в корзину"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('orders:add-to-cart')
        data = {
            'product_id': self.product.id,
            'quantity': 2
        }
        response = self.client.post(url, data, format='json')
        
        assert response.status_code == 200
        assert response.data['total'] == '998.00'
        assert response.data['items_count'] == 1
    
    def test_view_cart(self):
        """Тест просмотра корзины"""
        self.client.force_authenticate(user=self.user)
        
        # Добавляем товар в корзину
        add_url = reverse('orders:add-to-cart')
        self.client.post(add_url, {'product_id': self.product.id, 'quantity': 2}, format='json')
        
        # Просматриваем корзину
        url = reverse('orders:cart')
        response = self.client.get(url)
        
        assert response.status_code == 200
        assert response.data['total'] == '998.00'