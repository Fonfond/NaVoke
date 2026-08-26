# notifications/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import requests


@shared_task
def send_order_notification(order_id):
    """Отправка уведомления о новом заказе"""
    from orders.models import Order
    
    try:
        order = Order.objects.get(id=order_id)
        
        # Email администратору
        subject = f'🆕 Новый заказ #{order.order_number}'
        message = f'''
        Новый заказ #{order.order_number}
        
        Клиент: {order.user.full_name or order.user.username}
        Телефон: {order.user.phone or '—'}
        Сумма: {order.total_amount} ₽
        Способ получения: {order.get_delivery_type_display()}
        Адрес: {order.delivery_address}
        Статус: {order.get_status_display()}
        
        Ссылка на заказ: {settings.SITE_URL}/admin/orders/order/{order.id}/change/
        '''
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_EMAIL],
            fail_silently=True,
        )
        
        # Уведомление в Telegram (если настроен бот)
        if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
            send_telegram_notification(order)
        
        return f"Уведомление для заказа #{order.order_number} отправлено"
        
    except Order.DoesNotExist:
        return "Заказ не найден"


def send_telegram_notification(order):
    """Отправка уведомления в Telegram"""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return
    
    message = f'''
    🆕 <b>Новый заказ #{order.order_number}</b>
    
    👤 {order.user.full_name or order.user.username}
    📞 {order.user.phone or '—'}
    💰 {order.total_amount} ₽
    📦 {order.get_delivery_type_display()}
    📍 {order.delivery_address}
    
    Статус: {order.get_status_display()}
    '''
    
    try:
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': settings.TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        requests.post(url, data=data)
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")