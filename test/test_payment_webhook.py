# tests/test_payment_webhook.py
import logging
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from orders.models import Order
from payments.models import Payment
from users.models import User


@pytest.fixture(autouse=True)
def trusted_yookassa_settings(settings):
    settings.YOOKASSA_TRUSTED_NETS = ['203.0.113.0/24']
    settings.YOOKASSA_TRUST_PROXY = False


@pytest.mark.django_db
class TestPaymentWebhook:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='webhook-user',
            password='webhook-password-123',
            phone='+79990000100',
            role='client',
        )
        self.order = Order.objects.create(
            user=self.user,
            order_number='NVK-WEBHOOK-1',
            delivery_address='Тестовый адрес',
            subtotal=Decimal('100.00'),
            total_amount=Decimal('100.00'),
            payment_method='online',
        )
        self.payment = Payment.objects.create(
            order=self.order,
            payment_id='pay-test-1',
            amount=Decimal('100.00'),
            status='pending',
            payment_method='bank_card',
        )

    def _post(self, data=None, **extra):
        payload = data or {
            'event': 'payment.succeeded',
            'object': {'id': self.payment.payment_id},
        }
        return self.client.post(
            reverse('payments:payment-webhook'),
            payload,
            format='json',
            **extra,
        )

    def _remote_payment(self, **overrides):
        payload = {
            'id': self.payment.payment_id,
            'status': 'succeeded',
            'amount': {'value': '100.00', 'currency': 'RUB'},
            'metadata': {'order_id': self.order.id},
        }
        payload.update(overrides)
        return payload

    @patch('payments.views.YooKassaService.get_payment')
    def test_untrusted_ip_returns_403(self, mock_get_payment):
        response = self._post(REMOTE_ADDR='198.51.100.10')

        assert response.status_code == 403
        mock_get_payment.assert_not_called()
        self.order.refresh_from_db()
        assert self.order.payment_status == 'pending'

    @patch('payments.views.YooKassaService.get_payment')
    def test_unknown_payment_returns_404(self, mock_get_payment):
        response = self._post(
            data={
                'event': 'payment.succeeded',
                'object': {'id': 'pay-does-not-exist'},
            },
            REMOTE_ADDR='203.0.113.10',
        )

        assert response.status_code == 404
        mock_get_payment.assert_not_called()

    @patch('payments.views.YooKassaService.get_payment')
    def test_amount_mismatch_returns_409_and_logs(self, mock_get_payment, caplog):
        mock_get_payment.return_value = self._remote_payment(
            amount={'value': '999.00', 'currency': 'RUB'},
        )

        with caplog.at_level(logging.CRITICAL, logger='payments.views'):
            response = self._post(REMOTE_ADDR='203.0.113.10')

        assert response.status_code == 409
        assert 'YooKassa verification failed' in caplog.text
        self.order.refresh_from_db()
        assert self.order.payment_status == 'pending'
        self.payment.refresh_from_db()
        assert self.payment.status == 'pending'

    @patch('payments.views.YooKassaService.get_payment')
    def test_success_marks_order_paid(self, mock_get_payment):
        mock_get_payment.return_value = self._remote_payment()

        response = self._post(REMOTE_ADDR='203.0.113.10')

        assert response.status_code == 200
        self.order.refresh_from_db()
        assert self.order.payment_status == 'paid'
        assert self.order.status == 'confirmed'

        self.payment.refresh_from_db()
        assert self.payment.status == 'succeeded'
        assert self.payment.paid_at is not None

    @patch('payments.views.YooKassaService.get_payment')
    def test_repeated_success_is_idempotent(self, mock_get_payment):
        mock_get_payment.return_value = self._remote_payment()

        first = self._post(REMOTE_ADDR='203.0.113.10')
        assert first.status_code == 200

        self.payment.refresh_from_db()
        paid_at = self.payment.paid_at

        second = self._post(REMOTE_ADDR='203.0.113.10')
        assert second.status_code == 200

        self.order.refresh_from_db()
        self.payment.refresh_from_db()
        assert self.order.payment_status == 'paid'
        assert self.payment.paid_at == paid_at
        assert mock_get_payment.call_count == 1

    @patch('payments.views.YooKassaService.get_payment')
    def test_remote_pending_status_is_ignored(self, mock_get_payment):
        mock_get_payment.return_value = self._remote_payment(status='pending')

        response = self._post(REMOTE_ADDR='203.0.113.10')

        assert response.status_code == 200
        assert response.data['status'] == 'ignored'
        self.order.refresh_from_db()
        assert self.order.payment_status == 'pending'

    @patch('payments.views.YooKassaService.get_payment')
    def test_forwarded_header_is_not_trusted_without_proxy_flag(
        self, mock_get_payment
    ):
        response = self._post(
            REMOTE_ADDR='198.51.100.10',
            HTTP_X_FORWARDED_FOR='203.0.113.10',
        )

        assert response.status_code == 403
        mock_get_payment.assert_not_called()

    @patch('payments.views.YooKassaService.get_payment')
    def test_trusted_proxy_uses_real_ip(self, mock_get_payment, settings):
        settings.YOOKASSA_TRUST_PROXY = True
        mock_get_payment.return_value = self._remote_payment()

        response = self._post(
            REMOTE_ADDR='127.0.0.1',
            HTTP_X_REAL_IP='203.0.113.10',
        )

        assert response.status_code == 200
        self.order.refresh_from_db()
        assert self.order.payment_status == 'paid'
