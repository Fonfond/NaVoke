# orders/urls.py
from django.urls import path
from .views import (
    CartView, AddToCartView, UpdateCartItemView, 
    RemoveFromCartView, ClearCartView, GuestCartView,
    CreateOrderView, OrderListView, OrderDetailView, CancelOrderView, UpdatePaymentStatusView, UpdateOrderStatusView
)

app_name = 'orders'

urlpatterns = [
    # Корзина
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/add/', AddToCartView.as_view(), name='add-to-cart'),
    path('cart/update/<int:item_id>/', UpdateCartItemView.as_view(), name='update-cart-item'),
    path('cart/remove/<int:item_id>/', RemoveFromCartView.as_view(), name='remove-from-cart'),
    path('cart/clear/', ClearCartView.as_view(), name='clear-cart'),
    
    # Заказы
    path('<int:order_id>/update-payment-status/', UpdatePaymentStatusView.as_view(), name='update-payment-status'),
    path('', CreateOrderView.as_view(), name='create-order'),
    path('guest-cart/', GuestCartView.as_view(), name='guest-cart'),
    path('guest-cart/<int:item_id>/', GuestCartView.as_view(), name='guest-cart-item'),
    path('list/', OrderListView.as_view(), name='order-list'),
    path('<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('<int:order_id>/cancel/', CancelOrderView.as_view(), name='cancel-order'),
    path('<int:order_id>/update-status/', UpdateOrderStatusView.as_view(), name='update-order-status'),
]