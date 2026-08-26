# orders/admin.py
from django.contrib import admin
from .models import Order, OrderItem, Cart, CartItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('price_at_order',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'total_amount', 'status', 'payment_status', 'order_date')
    list_filter = ('status', 'payment_status', 'order_date')
    search_fields = ('order_number', 'user__username', 'user__phone')
    readonly_fields = ('order_number', 'order_date', 'subtotal', 'total_amount')
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('order_number', 'user', 'order_date', 'status')
        }),
        ('Доставка', {
            'fields': ('delivery_address', 'delivery_date', 'delivery_time_from', 'delivery_time_to', 'comment')
        }),
        ('Финансы', {
            'fields': ('subtotal', 'delivery_cost', 'discount', 'bonus_used', 'total_amount')
        }),
        ('Оплата', {
            'fields': ('payment_method', 'payment_status')
        }),
        ('Курьер', {
            'fields': ('courier',)
        }),
    )

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at', 'updated_at')
    search_fields = ('user__username',)

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'cart', 'product', 'quantity')
    search_fields = ('product__name',)