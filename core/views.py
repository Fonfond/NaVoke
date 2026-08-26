from django.shortcuts import render

# Create your views here.
# core/views.py
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import SiteSettings
from .serializers import SiteSettingsSerializer
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from orders.models import Order
from users.models import User


class SettingsView(APIView):
    """Получение и обновление настроек сайта"""
    permission_classes = (permissions.IsAuthenticated,)
    
    def get(self, request):
        # Проверяем, что пользователь админ
        if request.user.role != 'admin':
            return Response(
                {'error': 'Только администраторы могут просматривать настройки'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        settings = SiteSettings.get_settings()
        serializer = SiteSettingsSerializer(settings)
        return Response(serializer.data)
    
    def put(self, request):
        if request.user.role != 'admin':
            return Response(
                {'error': 'Только администраторы могут изменять настройки'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        settings = SiteSettings.get_settings()
        serializer = SiteSettingsSerializer(settings, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PublicSettingsView(APIView):
    """Публичные настройки (без авторизации)"""
    permission_classes = (permissions.AllowAny,)
    
    def get(self, request):
        settings = SiteSettings.get_settings()
        return Response({
            'banner_enabled': settings.banner_enabled,
            'banner_title': settings.banner_title,
            'banner_subtitle': settings.banner_subtitle,
            'banner_button_text': settings.banner_button_text,
            'banner_image_url': settings.banner_image_url,
            'banner_link': settings.banner_link,
            'delivery_free_threshold': settings.delivery_free_threshold,
            'delivery_base_cost': settings.delivery_base_cost,
            'bonus_enabled': settings.bonus_enabled,
            'bonus_rate': str(settings.bonus_rate),
            'bonus_min_order': settings.bonus_min_order,
            'contact_phone': settings.contact_phone,
            'contact_email': settings.contact_email,
            'contact_address': settings.contact_address,
            'working_hours': settings.working_hours,
            'site_name': settings.site_name,
            'lunch_title': settings.lunch_title,
            'lunch_items': settings.lunch_items,
        })


# ✅ НОВЫЙ КОНТРОЛЛЕР ДЛЯ АНАЛИТИКИ (ДОБАВЛЕН СЮДА)
class AnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Доступ запрещён'}, status=403)

        today = timezone.now().date()
        week_ago = today - timedelta(days=7)

        # 1. Заказы сегодня
        today_orders = Order.objects.filter(order_date__date=today)
        today_count = today_orders.count()
        today_revenue = today_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0

        # 2. Пользователи всего
        total_users = User.objects.count()

        # 3. Средний рейтинг (заглушка - можно посчитать через Review)
        avg_rating = 4.8

        # 4. Недельная выручка по дням
        weekly_data = []
        for i in range(7):
            day = today - timedelta(days=i)
            day_orders = Order.objects.filter(order_date__date=day)
            revenue = day_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            weekly_data.insert(0, float(revenue))  # вставляем в начало, чтобы дни шли по порядку

        # 5. Последние 5 заказов
        recent_orders = Order.objects.all().order_by('-order_date')[:5]
        orders_data = []
        for order in recent_orders:
            orders_data.append({
                'id': order.id,
                'order_number': order.order_number,
                'user_name': order.user.full_name or order.user.username,
                'total_amount': float(order.total_amount),
                'status': order.status,
            })

        return Response({
            'today_orders': today_count,
            'today_revenue': today_revenue,
            'total_users': total_users,
            'avg_rating': avg_rating,
            'weekly_revenue': weekly_data,
            'recent_orders': orders_data,
        })

# core/views.py
class SettingsView(APIView):
    """Получение и обновление настроек сайта"""
    permission_classes = (permissions.IsAuthenticated,)
    
    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Только администраторы могут просматривать настройки'}, status=status.HTTP_403_FORBIDDEN)
        
        settings = SiteSettings.get_settings()
        serializer = SiteSettingsSerializer(settings)
        return Response(serializer.data)
    
    def put(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Только администраторы могут изменять настройки'}, status=status.HTTP_403_FORBIDDEN)
        
        settings = SiteSettings.get_settings()
        serializer = SiteSettingsSerializer(settings, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    """Получение и обновление настроек сайта"""
    permission_classes = (permissions.IsAuthenticated,)
    
    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Только администраторы могут просматривать настройки'}, status=status.HTTP_403_FORBIDDEN)
        
        settings = SiteSettings.get_settings()
        serializer = SiteSettingsSerializer(settings)
        return Response(serializer.data)
    
    def put(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Только администраторы могут изменять настройки'}, status=status.HTTP_403_FORBIDDEN)
        
        settings = SiteSettings.get_settings()
        serializer = SiteSettingsSerializer(settings, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)