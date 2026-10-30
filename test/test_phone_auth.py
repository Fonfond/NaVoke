# tests/test_phone_auth.py
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from users.models import User
from users.utils import InvalidPhoneError, normalize_phone, try_normalize_phone


@pytest.mark.django_db
class TestPhoneAuth:
    def setup_method(self):
        self.client = APIClient()

    def test_register_normalizes_phone_and_username(self):
        response = self.client.post(
            reverse('users:register'),
            {
                'phone': '+7 (999) 123-45-67',
                'full_name': 'Тестовый Пользователь',
                'password': 'strong-password-123',
                'password2': 'strong-password-123',
            },
            format='json',
        )

        assert response.status_code == 201, response.data
        user = User.objects.get(phone='79991234567')
        assert user.username == '79991234567'
        assert response.data['user']['phone'] == '79991234567'
        assert response.data['user']['username'] == '79991234567'

    def test_login_accepts_formatted_phone(self):
        User.objects.create_user(
            username='79991234567',
            phone='79991234567',
            password='strong-password-123',
        )

        response = self.client.post(
            reverse('users:login'),
            {
                'username': '+7 999 123-45-67',
                'password': 'strong-password-123',
            },
            format='json',
        )

        assert response.status_code == 200, response.data
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_duplicate_phone_in_another_format_is_rejected(self):
        first = self.client.post(
            reverse('users:register'),
            {
                'phone': '+7 (999) 123-45-67',
                'full_name': 'Первый',
                'password': 'strong-password-123',
                'password2': 'strong-password-123',
            },
            format='json',
        )
        assert first.status_code == 201, first.data

        second = self.client.post(
            reverse('users:register'),
            {
                'phone': '8 999 123 45 67',
                'full_name': 'Второй',
                'password': 'strong-password-123',
                'password2': 'strong-password-123',
            },
            format='json',
        )

        assert second.status_code == 400
        assert 'phone' in second.data
        assert User.objects.count() == 1

    def test_profile_phone_is_normalized(self):
        user = User.objects.create_user(
            username='79991234567',
            phone='79991234567',
            password='strong-password-123',
        )
        self.client.force_authenticate(user=user)

        response = self.client.put(
            reverse('users:profile'),
            {'phone': '+7 (999) 123-45-67'},
            format='json',
        )

        assert response.status_code == 200, response.data
        user.refresh_from_db()
        assert user.phone == '79991234567'

    def test_normalize_phone_formats(self):
        assert normalize_phone('+7 (999) 123-45-67') == '79991234567'
        assert normalize_phone('8 999 123 45 67') == '79991234567'
        assert normalize_phone('9991234567') == '79991234567'
        assert try_normalize_phone('admin') is None

        with pytest.raises(InvalidPhoneError):
            normalize_phone('12345')
