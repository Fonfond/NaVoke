# core/models.py
from django.db import models


class SiteSettings(models.Model):
    """Настройки сайта"""
    
    # === БАННЕР ===
    banner_enabled = models.BooleanField(default=True, verbose_name='Баннер включён')
    banner_title = models.CharField(max_length=200, default='Скидка 20% на первый заказ', verbose_name='Заголовок баннера')
    banner_subtitle = models.CharField(max_length=300, default='При заказе от 800 ₽ — доставка бесплатно', verbose_name='Подзаголовок баннера')
    banner_button_text = models.CharField(max_length=50, default='Заказать', verbose_name='Текст кнопки')
    banner_image_url = models.URLField(blank=True, null=True, verbose_name='URL изображения')
    banner_link = models.URLField(blank=True, null=True, verbose_name='Ссылка с баннера')
    
    # === ДОСТАВКА ===
    delivery_free_threshold = models.PositiveIntegerField(default=800, verbose_name='Порог бесплатной доставки (₽)')
    delivery_base_cost = models.PositiveIntegerField(default=150, verbose_name='Базовая стоимость доставки (₽)')
    
    # === БОНУСЫ ===
    bonus_enabled = models.BooleanField(default=True, verbose_name='Бонусная система включена')
    bonus_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5.00, verbose_name='Бонусов за 100 ₽')
    bonus_min_order = models.PositiveIntegerField(default=300, verbose_name='Мин. заказ для начисления бонусов (₽)')
    bonus_max_percent = models.PositiveIntegerField(default=30, verbose_name='Макс. % оплаты бонусами')
    
    # === УВЕДОМЛЕНИЯ ===
    notifications_enabled = models.BooleanField(default=True, verbose_name='Уведомления включены')
    notification_email = models.EmailField(default='admin@navoke.ru', verbose_name='Email для уведомлений')
    notification_order_subject = models.CharField(max_length=200, default='Новый заказ на сайте', verbose_name='Тема письма о заказе')
    
    # === ОБЩИЕ ===
    site_name = models.CharField(max_length=100, default='НаVoke', verbose_name='Название сайта')
    contact_phone = models.CharField(max_length=20, default='+7 (999) 123-45-67', verbose_name='Телефон')
    contact_email = models.EmailField(default='info@navoke.ru', verbose_name='Email для связи')
    contact_address = models.TextField(default='пгт. Селенгинск, ул. Ленина, 10', verbose_name='Адрес')
    
    working_hours = models.CharField(max_length=200, default='Пн-Чт: 10:00 — 23:00, Пт-Вс: 11:00 — 00:00', verbose_name='Часы работы')
    
    # ✅ НОВЫЕ ПОЛЯ ДЛЯ БИЗНЕС-ЛАНЧА
    lunch_title = models.CharField(max_length=200, default='Бизнес-ланч', verbose_name='Заголовок бизнес-ланча')
    lunch_items = models.JSONField(default=list, verbose_name='Позиции бизнес-ланча')
    
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        db_table = 'site_settings'
        verbose_name = 'Настройка сайта'
        verbose_name_plural = 'Настройки сайта'
    
    def __str__(self):
        return f'Настройки сайта ({self.updated_at})'
    
    @classmethod
    def get_settings(cls):
        """Получить настройки (создаёт, если нет)"""
        settings, created = cls.objects.get_or_create(id=1)
        return settings