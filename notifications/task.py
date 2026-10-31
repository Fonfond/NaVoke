# notifications/task.py
import logging

try:
    from celery import shared_task
except ImportError:  # Celery is optional for local tests/shell usage.
    def shared_task(func):
        return func
from django.conf import settings
from django.core.mail import send_mail
import requests


logger = logging.getLogger(__name__)


def _send_one(subject, message, recipient):
    if not recipient:
        return False
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        logger.info('Email sent to %s: %s', recipient, subject)
        return True
    except Exception:
        logger.exception('Email failed to %s: %s', recipient, subject)
        return False


@shared_task
def send_order_notification(order_id):
    """Отправка уведомлений о новом заказе администратору и клиенту."""
    from orders.models import Order

    try:
        order = Order.objects.select_related('user').get(id=order_id)
    except Order.DoesNotExist:
        logger.warning('Order %s not found for email notification', order_id)
        return f'Заказ #{order_id} не найден'

    order_url = f'{settings.SITE_URL}/order/{order.id}/'
    admin_url = f'{settings.SITE_URL}/admin-panel/'

    admin_subject = f'🆕 Новый заказ #{order.order_number}'
    admin_message = f'''
Новый заказ #{order.order_number}

Клиент: {order.user.full_name or order.user.username}
Телефон: {order.user.phone or '—'}
Email: {order.user.email or '—'}
Сумма: {order.total_amount} ₽
Способ получения: {order.get_delivery_type_display()}
Адрес: {order.delivery_address or '—'}
Статус: {order.get_status_display()}

Открыть админку: {admin_url}
Заказ: {order_url}
'''

    customer_subject = f'✅ Заказ #{order.order_number} оформлен'
    customer_message = f'''
Здравствуйте, {order.user.full_name or order.user.username}!

Ваш заказ #{order.order_number} принят.

Сумма: {order.total_amount} ₽
Способ получения: {order.get_delivery_type_display()}
Адрес: {order.delivery_address or '—'}
Статус: {order.get_status_display()}

Посмотреть заказ: {order_url}

Спасибо, что выбрали НаVoke!
'''

    _send_one(admin_subject, admin_message, settings.ADMIN_EMAIL)
    if order.user.email:
        _send_one(customer_subject, customer_message, order.user.email)

    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
        send_telegram_notification(order)

    return f'Уведомления для заказа #{order.order_number} обработаны'


def send_telegram_notification(order):
    """Отправка уведомления в Telegram."""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return

    message = f'''
🆕 <b>Новый заказ #{order.order_number}</b>

👤 {order.user.full_name or order.user.username}
📞 {order.user.phone or '—'}
💰 {order.total_amount} ₽
📦 {order.get_delivery_type_display()}
📍 {order.delivery_address or '—'}

Статус: {order.get_status_display()}
'''

    try:
        url = f'https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage'
        data = {
            'chat_id': settings.TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML',
        }
        response = requests.post(url, data=data, timeout=10)
        if response.status_code >= 400:
            logger.warning(
                'Telegram notification failed with status %s: %s',
                response.status_code,
                response.text[:500],
            )
    except Exception:
        logger.exception('Telegram notification failed for order %s', order.id)
