# payments/models.py
from django.db import models
from orders.models import Order


class Payment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'В обработке'),
        ('waiting_for_capture', 'Ожидает подтверждения'),
        ('succeeded', 'Успешно'),
        ('canceled', 'Отменён'),
        ('refunded', 'Возвращён'),
    )
    
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name='payment')
    payment_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, default='unknown')
    
    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Платёж {self.payment_id} - {self.status}"