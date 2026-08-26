# payments/urls.py
from django.urls import path
from .views import CreatePaymentView, PaymentWebhookView, CheckPaymentStatusView

app_name = 'payments'

urlpatterns = [
    path('create/', CreatePaymentView.as_view(), name='create-payment'),
    path('webhook/', PaymentWebhookView.as_view(), name='payment-webhook'),
    path('<int:order_id>/status/', CheckPaymentStatusView.as_view(), name='payment-status'),
]