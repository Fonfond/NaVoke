# payments/services.py
import uuid
import requests
from django.conf import settings
from django.utils import timezone
from orders.models import Order
from .models import Payment


class YooKassaService:
    """Сервис для работы с API ЮKassa"""
    
    BASE_URL = 'https://api.yookassa.ru/v3'
    
    def __init__(self):
        self.shop_id = settings.YOOKASSA_SHOP_ID
        self.secret_key = settings.YOOKASSA_SECRET_KEY
        self.return_url = settings.YOOKASSA_RETURN_URL
    
    def create_payment(self, order: Order):
        """Создание платежа в ЮKassa"""
        idempotence_key = str(uuid.uuid4())
        
        data = {
            "amount": {
                "value": str(float(order.total_amount)),
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": self.return_url
            },
            "capture": True,
            "description": f"Заказ {order.order_number}",
            "metadata": {
                "order_id": order.id,
                "order_number": order.order_number
            }
        }
        
        response = requests.post(
            f"{self.BASE_URL}/payments",
            json=data,
            auth=(self.shop_id, self.secret_key),
            headers={
                'Idempotence-Key': idempotence_key,
                'Content-Type': 'application/json'
            }
        )
        
        if response.status_code in [200, 201]:
            payment_data = response.json()
            
            payment = Payment.objects.create(
                order=order,
                payment_id=payment_data['id'],
                amount=order.total_amount,
                status=payment_data['status'],
                payment_method=payment_data.get('payment_method', {}).get('type', 'unknown')
            )
            
            return {
                'payment_id': payment_data['id'],
                'confirmation_url': payment_data['confirmation']['confirmation_url'],
                'status': payment_data['status']
            }
        else:
            raise Exception(f"Ошибка создания платежа: {response.text}")
    
    def get_payment(self, payment_id: str):
        """Получение информации о платеже"""
        response = requests.get(
            f"{self.BASE_URL}/payments/{payment_id}",
            auth=(self.shop_id, self.secret_key)
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Ошибка получения платежа: {response.text}")
    
    def cancel_payment(self, payment_id: str):
        """Отмена платежа"""
        response = requests.post(
            f"{self.BASE_URL}/payments/{payment_id}/cancel",
            auth=(self.shop_id, self.secret_key),
            json={}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Ошибка отмены платежа: {response.text}")