# payments/views.py
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from orders.models import Order
from .models import Payment
from .services import YooKassaService


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
    """Webhook для обработки уведомлений от ЮKassa"""
    permission_classes = (permissions.AllowAny,)
    
    def post(self, request):
        event = request.data.get('event')
        payment_data = request.data.get('object')
        
        if not event or not payment_data:
            return Response({'error': 'Invalid webhook'}, status=status.HTTP_400_BAD_REQUEST)
        
        payment_id = payment_data['id']
        
        try:
            payment = Payment.objects.get(payment_id=payment_id)
            order = payment.order
            
            if event == 'payment.succeeded':
                order.payment_status = 'paid'
                order.status = 'confirmed'
                order.save()
                
                payment.status = 'succeeded'
                payment.paid_at = timezone.now()
                payment.save()
                
                # TODO: Отправить уведомление клиенту
                print(f"✅ Платёж {payment_id} успешен для заказа {order.order_number}")
            
            elif event == 'payment.canceled':
                payment.status = 'canceled'
                payment.save()
                
                order.payment_status = 'failed'
                order.save()
                
                print(f"❌ Платёж {payment_id} отменён для заказа {order.order_number}")
            
            elif event == 'payment.refunded':
                payment.status = 'refunded'
                payment.refunded_at = timezone.now()
                payment.save()
                
                order.payment_status = 'refunded'
                order.save()
                
                print(f"🔄 Платёж {payment_id} возвращён для заказа {order.order_number}")
        
        except Payment.DoesNotExist:
            return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({'status': 'ok'})


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