# tests/test_users.py
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from users.models import User


@pytest.mark.django_db
class TestUserAPI:
    
    def setup_method(self):
        self.client = APIClient()
    
    def test_register_user(self):
        """Тест регистрации пользователя"""
        url = reverse('users:register')
        data = {
            'username': 'testuser',
            'email': 'test@mail.ru',
            'phone': '+79991234567',
            'full_name': 'Тестовый Пользователь',
            'password': '12345678',
            'password2': '12345678'
        }
        response = self.client.post(url, data, format='json')
        
        assert response.status_code == 201
        assert 'access' in response.data
        assert response.data['user']['username'] == 'testuser'
    
    def test_login_user(self):
        """Тест входа пользователя"""
        # Создаём пользователя
        User.objects.create_user(
            username='testuser',
            password='12345678',
            phone='+79991234567'
        )
        
        url = reverse('users:login')
        data = {
            'username': 'testuser',
            'password': '12345678'
        }
        response = self.client.post(url, data, format='json')
        
        assert response.status_code == 200
        assert 'access' in response.data
        assert 'refresh' in response.data
    
    def test_profile(self):
        """Тест получения профиля"""
        user = User.objects.create_user(
            username='testuser',
            password='12345678'
        )
        
        self.client.force_authenticate(user=user)
        url = reverse('users:profile')
        response = self.client.get(url)
        
        assert response.status_code == 200
        assert response.data['username'] == 'testuser'