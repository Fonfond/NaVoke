# tests/test_order_status.py
from decimal import Decimal
from uuid import uuid4

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from orders.models import Order, OrderStatusHistory
from products.models import Category, Product
from users.models import User


@pytest.mark.django_db
class TestOrderStatusFSM:
    def setup_method(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='status-admin',
            password='admin-password-123',
            phone='+79990000300',
            role='admin',
        )
        self.customer = User.objects.create_user(
            username='status-customer',
            password='customer-password-123',
            phone='+79990000301',
            role='client',
        )
        self.category = Category.objects.create(name='Роллы', slug='rolls')
        self.product = Product.objects.create(
            name='Филадельфия',
            category=self.category,
            price=Decimal('1000.00'),
            weight=250,
        )
        self.client.force_authenticate(user=self.admin)

    def _order(self, **overrides):
        values = {
            'user': self.customer,
            'order_number': f'NVK-STATUS-{uuid4().hex[:8].upper()}',
            'delivery_address': 'Тестовый адрес',
            'subtotal': Decimal('1000.00'),
            'total_amount': Decimal('1000.00'),
            'payment_method': 'online',
            'payment_status': 'pending',
            'status': 'new',
        }
        values.update(overrides)
        return Order.objects.create(**values)

    def _put_status(self, order, new_status):
        return self.client.put(
            reverse('orders:update-order-status', kwargs={'order_id': order.id}),
            {'status': new_status},
            format='json',
        )

    def test_new_to_delivered_is_forbidden(self):
        order = self._order(status='new')

        response = self._put_status(order, 'delivered')

        assert response.status_code == 409
        order.refresh_from_db()
        assert order.status == 'new'
        assert OrderStatusHistory.objects.filter(order=order).count() == 0

    def test_delivered_to_cancelled_is_forbidden(self):
        order = self._order(status='delivered', payment_status='paid')

        response = self._put_status(order, 'cancelled')

        assert response.status_code == 409
        order.refresh_from_db()
        assert order.status == 'delivered'
        assert OrderStatusHistory.objects.filter(order=order).count() == 0

    def test_online_unpaid_delivery_is_forbidden(self):
        order = self._order(
            status='ready',
            payment_method='online',
            payment_status='pending',
        )

        response = self._put_status(order, 'delivered')

        assert response.status_code == 409
        order.refresh_from_db()
        assert order.status == 'ready'
        assert OrderStatusHistory.objects.filter(order=order).count() == 0

    def test_new_to_confirmed_records_history(self):
        order = self._order(status='new')

        response = self._put_status(order, 'confirmed')

        assert response.status_code == 200, response.data
        order.refresh_from_db()
        assert order.status == 'confirmed'

        history = OrderStatusHistory.objects.get(order=order)
        assert history.from_status == 'new'
        assert history.to_status == 'confirmed'
        assert history.changed_by == self.admin

    def test_cancel_records_history(self):
        order = self._order(status='new')
        self.client.force_authenticate(user=self.customer)

        response = self.client.post(
            reverse('orders:cancel-order', kwargs={'order_id': order.id}),
        )

        assert response.status_code == 200, response.data
        order.refresh_from_db()
        assert order.status == 'cancelled'

        history = OrderStatusHistory.objects.get(order=order)
        assert history.from_status == 'new'
        assert history.to_status == 'cancelled'
        assert history.changed_by == self.customer

    def test_paid_delivery_awards_bonus_once(self):
        order = self._order(
            status='ready',
            payment_method='online',
            payment_status='paid',
            total_amount=Decimal('1000.00'),
        )

        first = self._put_status(order, 'delivered')
        assert first.status_code == 200, first.data

        order.refresh_from_db()
        self.customer.refresh_from_db()
        assert order.status == 'delivered'
        assert self.customer.bonus_points == 50
        assert OrderStatusHistory.objects.filter(order=order).count() == 1

        second = self._put_status(order, 'delivered')
        assert second.status_code == 409

        self.customer.refresh_from_db()
        assert self.customer.bonus_points == 50
        assert OrderStatusHistory.objects.filter(order=order).count() == 1

    def test_cash_delivery_is_allowed_without_prepayment(self):
        order = self._order(
            status='ready',
            payment_method='cash',
            payment_status='pending',
        )

        response = self._put_status(order, 'delivered')

        assert response.status_code == 200, response.data
        order.refresh_from_db()
        assert order.status == 'delivered'
        assert OrderStatusHistory.objects.filter(order=order).count() == 1

    def test_admin_cancel_refunds_bonus_and_records_history(self):
        User.objects.filter(pk=self.customer.pk).update(bonus_points=800)
        order = self._order(
            status='new',
            total_amount=Decimal('800.00'),
            bonus_used=200,
        )

        response = self._put_status(order, 'cancelled')

        assert response.status_code == 200, response.data
        order.refresh_from_db()
        self.customer.refresh_from_db()
        assert order.status == 'cancelled'
        assert self.customer.bonus_points == 1000

        history = OrderStatusHistory.objects.get(order=order)
        assert history.from_status == 'new'
        assert history.to_status == 'cancelled'
        assert history.changed_by == self.admin
