from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from orders.models import Cart, CartItem, Order
from products.models import Category, Product
from users.models import User


@pytest.mark.django_db
class TestOrderEmailNotifications:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='email-client',
            password='email-password-123',
            phone='+79990000300',
            email='client@example.com',
            role='client',
        )
        self.category = Category.objects.create(name='Роллы', slug='rolls')
        self.product = Product.objects.create(
            name='Филадельфия',
            category=self.category,
            price=Decimal('1000.00'),
            weight=250,
        )
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        self.client.force_authenticate(user=self.user)

    def _payload(self):
        return {
            'payment_method': 'cash',
            'delivery_type': 'pickup',
            'delivery_address': 'Тестовый адрес',
            'bonus_used': 0,
        }

    def test_order_creation_sends_admin_and_customer_email(
        self,
        django_capture_on_commit_callbacks,
        mailoutbox,
        settings,
    ):
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        settings.ADMIN_EMAIL = 'admin@test.local'
        settings.DEFAULT_FROM_EMAIL = 'noreply@test.local'
        mailoutbox.clear()

        with django_capture_on_commit_callbacks(execute=True):
            response = self.client.post(
                reverse('orders:create-order'),
                self._payload(),
                format='json',
            )

        assert response.status_code == 201, response.data
        order = Order.objects.get(id=response.data['id'])
        assert len(mailoutbox) == 2

        admin_email = next(
            email for email in mailoutbox
            if email.to == ['admin@test.local']
        )
        customer_email = next(
            email for email in mailoutbox
            if email.to == ['client@example.com']
        )

        assert order.order_number in admin_email.subject
        assert order.order_number in customer_email.subject
        assert admin_email.from_email == 'noreply@test.local'
        assert customer_email.from_email == 'noreply@test.local'
        assert 'Филадельфия' not in admin_email.body
        assert '1000' in customer_email.body

    def test_smtp_failure_does_not_rollback_order(
        self,
        django_capture_on_commit_callbacks,
        mailoutbox,
        monkeypatch,
        settings,
    ):
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        settings.ADMIN_EMAIL = 'admin@test.local'
        settings.DEFAULT_FROM_EMAIL = 'noreply@test.local'
        mailoutbox.clear()

        def fail_send(*args, **kwargs):
            raise RuntimeError('SMTP is down')

        monkeypatch.setattr('notifications.task.send_mail', fail_send)

        with django_capture_on_commit_callbacks(execute=True):
            response = self.client.post(
                reverse('orders:create-order'),
                self._payload(),
                format='json',
            )

        assert response.status_code == 201, response.data
        assert Order.objects.filter(id=response.data['id']).exists()
        assert mailoutbox == []

    def test_empty_customer_email_sends_only_admin(
        self,
        django_capture_on_commit_callbacks,
        mailoutbox,
        settings,
    ):
        self.user.email = ''
        self.user.save(update_fields=['email'])
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        settings.ADMIN_EMAIL = 'admin@test.local'
        settings.DEFAULT_FROM_EMAIL = 'noreply@test.local'
        mailoutbox.clear()

        with django_capture_on_commit_callbacks(execute=True):
            response = self.client.post(
                reverse('orders:create-order'),
                self._payload(),
                format='json',
            )

        assert response.status_code == 201, response.data
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == ['admin@test.local']
