# payments/views.py
import ipaddress
import logging
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from orders.models import Order
from .models import Payment
from .services import YooKassaAPIError, YooKassaService


logger = logging.getLogger(__name__)


def _client_ip(request):
    """IP клиента с учётом доверенного reverse-proxy."""
    if settings.YOOKASSA_TRUST_PROXY:
        real_ip = request.META.get('HTTP_X_REAL_IP')
        if real_ip:
            return real_ip.strip()
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if forwarded:
            # Последний адрес добавлен ближайшим доверенным прокси;
            # первый клиент может подставить сам.
            return forwarded.split(',')[-1].strip()
    return request.META.get('REMOTE_ADDR', '').strip()


def _is_trusted_ip(ip):
    try:
        address = ipaddress.ip_address(ip)
        networks = [
            net if isinstance(net, (ipaddress.IPv4Network, ipaddress.IPv6Network))
            else ipaddress.ip_network(net, strict=False)
            for net in settings.YOOKASSA_TRUSTED_NETS
        ]
    except ValueError:
        logger.error('Invalid client IP or YOOKASSA_TRUSTED_NETS: %s', ip)
        return False

    return any(
        address.version == net.version and address in net
        for net in networks
    )


class CreatePaymentView(APIView):
    """Создание платежа для заказа"""
    permission_classes = (permissions.IsAuthenticated,)
    
    def post(self, request):
        order_id = request.data.get('order_id')
        
        if not order_id:
            return Response(
                {'error': 'Не указан ID заказа'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response(
                {'error': 'Заказ не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Проверяем, не оплачен ли уже заказ
        if order.payment_status == 'paid':
            return Response(
                {'error': 'Заказ уже оплачен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем, не создан ли уже платёж
        if hasattr(order, 'payment'):
            payment = order.payment
            if payment.status == 'pending':
                service = YooKassaService()
                try:
                    payment_data = service.get_payment(payment.payment_id)
                    return Response({
                        'payment_id': payment_data['id'],
                        'confirmation_url': payment_data['confirmation']['confirmation_url'],
                        'status': payment_data['status']
                    })
                except:
                    pass
        
        service = YooKassaService()
        try:
            payment_data = service.create_payment(order)
            return Response(payment_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class PaymentWebhookView(APIView):
    """Webhook для обработки уведомлений от ЮKassa."""
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    def post(self, request):
        ip = _client_ip(request)
        if not _is_trusted_ip(ip):
            logger.warning('Rejected YooKassa webhook from %s', ip)
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        event = request.data.get('event')
        payment_data = request.data.get('object') or {}
        payment_id = payment_data.get('id')

        if not event or not payment_id:
            return Response(
                {'error': 'Invalid webhook'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # В рамках C-1 обрабатываем только подтверждённую оплату.
        # Отмена/возврат требуют отдельного refund-flow и не меняются по телу запроса.
        if event != 'payment.succeeded':
            return Response({'status': 'ignored'}, status=status.HTTP_200_OK)

        try:
            payment = Payment.objects.select_related('order').get(payment_id=payment_id)
        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        order = payment.order
        if order.payment_status == 'paid':
            return Response({'status': 'ok'}, status=status.HTTP_200_OK)

        # Не доверяем телу запроса: проверяем реальный статус и сумму в API.
        try:
            remote = YooKassaService().get_payment(payment_id)
        except YooKassaAPIError:
            logger.exception('YooKassa API unavailable for payment %s', payment_id)
            return Response(
                {'error': 'Payment provider unavailable'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if remote.get('status') != 'succeeded':
            return Response({'status': 'ignored'}, status=status.HTTP_200_OK)

        try:
            remote_amount = Decimal(str(remote['amount']['value']))
        except (KeyError, TypeError, InvalidOperation):
            logger.critical('Malformed YooKassa amount for payment %s', payment_id)
            return Response(
                {'error': 'Malformed payment data'},
                status=status.HTTP_409_CONFLICT,
            )

        currency = (remote.get('amount') or {}).get('currency')
        remote_order_id = str((remote.get('metadata') or {}).get('order_id'))

        if (
            str(remote.get('id')) != str(payment_id)
            or currency != 'RUB'
            or remote_amount != order.total_amount
            or payment.amount != order.total_amount
            or remote_order_id != str(order.id)
        ):
            logger.critical(
                'YooKassa verification failed payment=%s order=%s '
                'remote_amount=%s order_total=%s currency=%s metadata_order=%s',
                payment_id,
                order.id,
                remote_amount,
                order.total_amount,
                currency,
                remote_order_id,
            )
            return Response(
                {'error': 'Payment verification failed'},
                status=status.HTTP_409_CONFLICT,
            )

        # Блокируем строки только после ответа внешнего API.
        with transaction.atomic():
            try:
                payment = Payment.objects.select_for_update().get(pk=payment.pk)
                order = Order.objects.select_for_update().get(pk=payment.order_id)
            except (Payment.DoesNotExist, Order.DoesNotExist):
                return Response(
                    {'error': 'Payment not found'},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if order.payment_status == 'paid':
                return Response({'status': 'ok'}, status=status.HTTP_200_OK)

            if order.status == 'cancelled':
                logger.critical(
                    'YooKassa succeeded for cancelled order %s (payment %s)',
                    order.id,
                    payment_id,
                )
                return Response(
                    {'error': 'Order cancelled'},
                    status=status.HTTP_409_CONFLICT,
                )

            if (
                payment.amount != order.total_amount
                or remote_amount != order.total_amount
            ):
                logger.critical(
                    'Order total changed during YooKassa webhook order=%s '
                    'payment=%s',
                    order.id,
                    payment_id,
                )
                return Response(
                    {'error': 'Amount changed'},
                    status=status.HTTP_409_CONFLICT,
                )

            payment.status = 'succeeded'
            payment.paid_at = timezone.now()
            payment.save(update_fields=['status', 'paid_at'])

            order.payment_status = 'paid'
            if order.status == 'new':
                order.status = 'confirmed'
            order.save(update_fields=['payment_status', 'status'])

        return Response({'status': 'ok'}, status=status.HTTP_200_OK)


class CheckPaymentStatusView(APIView):
    """Проверка статуса платежа"""
    permission_classes = (permissions.IsAuthenticated,)
    
    def get(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response(
                {'error': 'Заказ не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not hasattr(order, 'payment'):
            return Response(
                {'status': 'no_payment'},
                status=status.HTTP_200_OK
            )
        
        payment = order.payment
        return Response({
            'payment_id': payment.payment_id,
            'status': payment.status,
            'paid_at': payment.paid_at,
            'amount': str(payment.amount)
        })